import asyncio
import gzip
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import anyio
import httpx
import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from app import observability as obs
from app.mcp_client import MCPToolClient


def test_metadata_mask_removes_content_and_untrusted_metadata(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_CONTENT_MODE", "metadata")
    attrs = {"langfuse.observation.input": "patient name",
             "langfuse.observation.output": "medical text",
             "langfuse.observation.metadata.credentials": "secret",
             "langfuse.observation.metadata.provider": '"openrouter"',
             "langfuse.observation.status_message": "secret error",
             "gen_ai.usage.input_tokens": 20}
    result = obs.mask_exports(params=SimpleNamespace(spans={"one": SimpleNamespace(attributes=attrs)}))
    deleted = result.span_patches["one"].delete_attributes
    assert set(deleted) == set(attrs) - {"langfuse.observation.metadata.provider", "gen_ai.usage.input_tokens"}


def test_exporter_creation_failure_does_not_break_application(monkeypatch):
    monkeypatch.setattr(obs, "_initialized", False)
    monkeypatch.setattr(obs, "_client", None)
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(key, "test")
    with patch("langfuse.Langfuse", side_effect=RuntimeError("SDK unavailable")):
        with obs.request_trace("test", uuid.uuid4().hex):
            assert obs.mcp_metadata() is None


def test_tracing_does_not_swallow_application_error(monkeypatch):
    monkeypatch.setattr(obs, "get_client", lambda: None)
    with pytest.raises(ValueError, match="application failure"):
        with obs.observation("test"):
            raise ValueError("application failure")


@pytest.fixture
def collector(monkeypatch):
    """Receive real SDK OTLP exports locally; never contact Langfuse Cloud."""
    spans = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            if self.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            request = ExportTraceServiceRequest.FromString(raw)
            for resource in request.resource_spans:
                for scope in resource.scope_spans:
                    spans.extend(scope.spans)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("OBSERVABILITY_CONTENT_MODE", "metadata")
    monkeypatch.setenv("LANGFUSE_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test-" + uuid.uuid4().hex)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test-not-a-real-secret")
    monkeypatch.setenv("LANGFUSE_FLUSH_INTERVAL", "0.1")
    monkeypatch.setattr(obs, "_client", None)
    monkeypatch.setattr(obs, "_initialized", False)
    yield spans
    obs.shutdown()
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_real_mcp_subprocess_keeps_concurrent_parent_context_and_masks_content(collector):
    async def run():
        client = MCPToolClient()
        await client.start()
        try:
            async def one():
                session = uuid.uuid4().hex
                with obs.request_trace("test-analysis", session, input="SENSITIVE_FIXTURE"):
                    parent = obs.mcp_metadata()
                    result = await client.call_tool("classify_lab_result", {
                        "test_name": "SENSITIVE_FIXTURE", "value": 14.2, "unit": "g/dL",
                        "min_ref": 12, "max_ref": 16,
                    })
                    assert result["status"] == "Normal"
                    assert obs.mcp_metadata() == parent
                    return parent, session
            parents = await asyncio.gather(one(), one())
            # Give the subprocess exporter a turn before closing its stdio session.
            await asyncio.sleep(0.5)
            return parents
        finally:
            await client.stop()

    parents = anyio.run(run)
    obs.get_client().flush()
    roots = [s for s in collector if s.name == "test-analysis"]
    tools = [s for s in collector if s.name == "classify-lab-result"]
    assert len(roots) == len(tools) == 2
    assert len({s.trace_id for s in roots}) == 2
    for carrier, session in parents:
        _, trace, parent, _ = carrier["traceparent"].split("-")
        tool = next(s for s in tools if s.trace_id.hex() == trace)
        assert tool.parent_span_id.hex() == parent
        attrs = {a.key: a.value.string_value for a in tool.attributes}
        assert attrs["session.id"] == session
    assert "SENSITIVE_FIXTURE" not in str(collector)
    assert obs.session_id() is None


def test_real_openai_wrapper_records_one_generation_and_usage(collector, monkeypatch):
    from app import llm
    OpenAI, traced = obs.openai_class()
    assert traced

    def reply(request):
        return httpx.Response(200, json={
            "id": "synthetic-response", "object": "chat.completion", "created": 1,
            "model": "qwen/test", "choices": [{"index": 0, "finish_reason": "stop",
             "message": {"role": "assistant", "content": "SENSITIVE_FIXTURE"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14, "cost": 0.0001},
        })

    def local_client(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(reply)))

    monkeypatch.setattr(llm, "openai_class", lambda: (local_client, True))
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-a-real-key")
    monkeypatch.setenv("LLM_MODEL", "qwen/test")
    with obs.request_trace("test-generation", uuid.uuid4().hex):
        assert llm._call_openrouter("SENSITIVE_FIXTURE", None) == "SENSITIVE_FIXTURE"
    obs.get_client().flush()
    generations = [s for s in collector if any(
        a.key == "langfuse.observation.type" and a.value.string_value == "generation" for a in s.attributes)]
    assert len(generations) == 1
    attrs = {a.key: a.value.string_value for a in generations[0].attributes}
    assert "10" in attrs["langfuse.observation.usage_details"]
    assert "0.0001" in attrs["langfuse.observation.cost_details"]
    assert "SENSITIVE_FIXTURE" not in str(collector)


def test_mcp_propagates_fallback_outcome_back_to_request(collector, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "no-provider-for-this-test")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "")

    async def run():
        client = MCPToolClient()
        await client.start()
        try:
            with obs.request_trace("test-fallback", uuid.uuid4().hex):
                result = await client.call_tool("translate_to_english", {"texts": ["synthetic"]})
                assert result["source"] == "fallback"
                assert {"llm-unavailable", "tool-fallback"} <= obs._outcome.get()
        finally:
            await client.stop()

    anyio.run(run)


def test_fallback_and_empty_completion_are_recorded(monkeypatch):
    from app import llm
    monkeypatch.setattr(obs, "get_client", lambda: None)
    monkeypatch.setenv("LLM_PROVIDER", "test-primary")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "test-fallback")
    monkeypatch.setitem(llm._PROVIDERS, "test-primary", lambda *_: "")
    monkeypatch.setitem(llm._PROVIDERS, "test-fallback", lambda *_: "answer")
    with obs.request_trace("test", uuid.uuid4().hex):
        assert llm.call_llm("synthetic") == "answer"
        assert {"empty-completion", "provider-fallback"} <= obs._outcome.get()


def test_graph_interrupt_closes_spans_and_chat_turns_have_distinct_traces(collector):
    from app.agent import analyze_labs, ask_followup

    class Tools:
        async def call_tool(self, name, args):
            if name == "translate_to_english":
                return {"translations": args["texts"], "source": "noop"}
            if name == "classify_lab_result":
                return {"test_name": args["test_name"], "value": args["value"],
                        "unit": args["unit"], "status": "Normal", "reference_range": "12-16"}
            if name == "explain_result":
                return {"explanation": "SENSITIVE_FIXTURE"}
            if name == "answer_followup":
                return {"answer": "SENSITIVE_FIXTURE"}
            raise AssertionError(name)

    async def run():
        tools = Tools()
        session = uuid.uuid4().hex
        with obs.request_trace("analyze-labs", session):
            result = await analyze_labs(tools, [{"Test_Name": "Hemoglobin", "Result": 14,
                "Unit": "g/dL", "Min_Reference": 12, "Max_Reference": 16}])
        turns = []
        with obs.observation("ambient-websocket"):
            for _ in range(2):
                telemetry = {}
                assert await ask_followup(tools, result["thread_id"], "SENSITIVE_FIXTURE", telemetry) == "SENSITIVE_FIXTURE"
                turns.append(telemetry)
        assert len({result["trace_id"], *(t["trace_id"] for t in turns)}) == 3
        assert all(t["session_id"] == session for t in turns)

    anyio.run(run)
    obs.get_client().flush()
    chats = [s for s in collector if s.name == "answer-followup"]
    assert len(chats) == 2
    assert all(s.end_time_unix_nano for s in collector)
    assert "SENSITIVE_FIXTURE" not in str(collector)
