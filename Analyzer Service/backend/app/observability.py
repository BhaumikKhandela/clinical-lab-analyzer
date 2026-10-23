"""Fail-open Langfuse tracing shared by the API and its MCP subprocess.

Request context lives in ContextVars/OTel context, never in a shared global.
Only the SDK client is process-scoped. Content export is opt-in for synthetic
fixtures; metadata mode strips automatic framework/client input and output.
"""

import logging
import os
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar

from app.config import settings  # Load this service's .env before SDK imports.

log = logging.getLogger("agent.observability")
_client = None
_initialized = False
_session = ContextVar("analysis_session", default=None)
_outcome = ContextVar("analysis_outcome", default=None)
_tool = ContextVar("analysis_tool", default=None)
SAFE_METADATA = {
    "provider", "attempt", "provider_fallback", "empty_completion", "finish_reason",
    "returned_model", "fallback_used", "found", "degraded_reasons", "rows_submitted",
    "rows_extracted", "rows_rejected", "critical", "warning", "normal", "unknown",
    "input_truncated", "text_characters", "validation_attempt", "langgraph_node",
    "ls_model_name", "ls_provider", "ls_model_type",
    "error_type",
    "row_index",
}
DEGRADATION_REASONS = {"empty-completion", "provider-fallback", "llm-unavailable",
                       "completion-truncated", "extraction-input-truncated",
                       "extraction-schema-retry", "tool-fallback", "lookup-no-result", "row-errors"}


def capture_content():
    return os.getenv("OBSERVABILITY_CONTENT_MODE", "metadata") == "synthetic"


def mask_exports(*, params):
    """Last defense for automatic OpenAI/LangGraph IO capture."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    patches = {}
    for identifier, span in params.spans.items():
        delete = []
        for key in span.attributes:
            lower = key.lower()
            content = (
                lower.endswith((".input", ".output"))
                or lower.startswith(("gen_ai.prompt.", "gen_ai.completion."))
            )
            sensitive_error = "status_message" in lower or lower.startswith("exception.")
            # Framework metadata can contain arbitrary request state.
            metadata = "metadata" in lower and key.rsplit(".", 1)[-1] not in SAFE_METADATA
            if metadata or sensitive_error or (content and not capture_content()):
                delete.append(key)
        if delete:
            patches[identifier] = OtelSpanPatch(delete_attributes=tuple(delete))
    return MaskOtelSpansResult(span_patches=patches)


def get_client():
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    if os.getenv("OBSERVABILITY_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return None
    if not all(os.getenv(k) for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")):
        log.info("Langfuse not configured; analysis continues without tracing")
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(mask_otel_spans=mask_exports,
                           environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"))
    except Exception as exc:
        log.warning("Langfuse initialization unavailable (%s)", type(exc).__name__)
    return _client


class Observation:
    """Telemetry failures must not swallow or replace application failures."""

    def __init__(self, span=None):
        self.span = span

    def update(self, **kwargs):
        if self.span is not None:
            try:
                self.span.update(**kwargs)
            except Exception as exc:
                log.warning("Trace update unavailable (%s)", type(exc).__name__)


@contextmanager
def observation(name, *, as_type="span", input=None, metadata=None):
    stack = ExitStack()
    wrapped = Observation()
    client = get_client()
    if client is not None:
        try:
            wrapped = Observation(stack.enter_context(client.start_as_current_observation(
                name=name, as_type=as_type,
                input=input if capture_content() else None,
                metadata=metadata,
            )))
        except Exception as exc:
            log.warning("Trace creation unavailable (%s)", type(exc).__name__)
    try:
        yield wrapped
    except BaseException as exc:
        # Do not hand raw exception messages/tracebacks to the SDK context manager.
        wrapped.update(level="ERROR", metadata={"error_type": type(exc).__name__})
        raise
    finally:
        try:
            stack.close()
        except Exception as exc:
            log.warning("Trace completion unavailable (%s)", type(exc).__name__)


def session_id():
    return _session.get()


def trace_id():
    client = get_client()
    if client is not None:
        try:
            return client.get_current_trace_id()
        except Exception:
            pass
    return None


def mark_degraded(reason):
    state = _outcome.get()
    if state is not None and reason in DEGRADATION_REASONS:
        state.add(reason)


@contextmanager
def outcome_scope():
    reasons = set()
    token = _outcome.set(reasons)
    try:
        yield reasons
    finally:
        _outcome.reset(token)


@contextmanager
def request_trace(name, session, *, input=None):
    token = _session.set(session)
    outcome_token = _outcome.set(set())
    stack = ExitStack()
    context_token = None
    try:
        if get_client() is not None:
            try:
                from langfuse import propagate_attributes
                from opentelemetry import context

                # A WebSocket may carry ambient context for its entire lifetime.
                # Every analysis/turn is an independent unit; session_id links it.
                context_token = context.attach(context.Context())
                stack.enter_context(propagate_attributes(session_id=session))
            except Exception:
                log.warning("Session propagation unavailable")
        with observation(name, input=input) as root:
            try:
                yield root
            finally:
                reasons = sorted(_outcome.get())
                if reasons:
                    root.update(metadata={"degraded_reasons": reasons}, level="WARNING")
    finally:
        try:
            stack.close()
        except Exception:
            log.warning("Session completion unavailable")
        if context_token is not None:
            from opentelemetry import context
            context.detach(context_token)
        _outcome.reset(outcome_token)
        _session.reset(token)


def mcp_metadata():
    """Propagate only trace context and a server-created session identifier."""
    if get_client() is None:
        return None
    try:
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        carrier = {}
        TraceContextTextMapPropagator().inject(carrier)
        if not carrier:
            return None
        if session_id():
            carrier["analysis_session_id"] = session_id()
        return carrier
    except Exception:
        log.warning("MCP trace injection unavailable")
        return None


@contextmanager
def incoming_mcp_context(meta):
    stack = ExitStack()
    otel_token = None
    session_token = None
    try:
        if meta and get_client() is not None:
            try:
                from opentelemetry import context
                from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
                from langfuse import propagate_attributes

                carrier = {k: v for k, v in meta.items()
                           if k in ("traceparent", "tracestate") and isinstance(v, str)}
                otel_token = context.attach(TraceContextTextMapPropagator().extract(carrier))
                session = meta.get("analysis_session_id")
                if isinstance(session, str) and len(session) == 32 and all(c in "0123456789abcdef" for c in session):
                    session_token = _session.set(session)
                    stack.enter_context(propagate_attributes(session_id=session))
            except Exception:
                log.warning("MCP trace extraction unavailable")
        yield
    finally:
        try:
            stack.close()
        finally:
            if session_token is not None:
                _session.reset(session_token)
            if otel_token is not None:
                from opentelemetry import context
                context.detach(otel_token)


def tool_operation():
    return _tool.get() or "response"


@contextmanager
def tool_trace(name, arguments):
    token = _tool.set(name.replace("_", "-"))
    kind = "retriever" if name in ("pubmed_search", "web_search", "search_clinical_context") else "tool"
    try:
        with observation(name.replace("_", "-"), as_type=kind, input=arguments) as span:
            try:
                yield span
            finally:
                reasons = _outcome.get()
                if reasons:
                    span.update(level="WARNING", metadata={"degraded_reasons": sorted(reasons)})
    finally:
        _tool.reset(token)


def graph_callbacks():
    if get_client() is None:
        return []
    try:
        from langfuse.langchain import CallbackHandler

        class SafeCallbackHandler(CallbackHandler):
            def on_chain_error(self, error, **kwargs):
                # GraphInterrupt is normal control flow for parked chat.
                if type(error).__name__ in ("GraphInterrupt", "NodeInterrupt"):
                    return super().on_chain_end({"awaiting": "question"}, **kwargs)
                return super().on_chain_error(RuntimeError(type(error).__name__), **kwargs)

        return [SafeCallbackHandler(public_key=os.environ["LANGFUSE_PUBLIC_KEY"])]
    except Exception as exc:
        log.warning("Graph tracing unavailable (%s)", type(exc).__name__)
        return []


def openai_class():
    if get_client() is not None:
        try:
            from langfuse.openai import OpenAI
            return OpenAI, True
        except Exception:
            log.warning("OpenAI tracing unavailable; using standard client")
    from openai import OpenAI
    return OpenAI, False


def shutdown():
    if _client is not None:
        try:
            _client.flush()
            _client.shutdown()
        except Exception as exc:
            log.warning("Langfuse shutdown unavailable (%s)", type(exc).__name__)
