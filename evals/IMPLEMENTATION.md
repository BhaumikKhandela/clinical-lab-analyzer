# Running DeepEval experiments

DeepEval 4.3.0 is installed in `evals/.venv`, isolated from the running backend.
The application adapters run with its existing backend virtual environment.
No production request hooks, VLMs, or new provider credentials are required.

## Commands

From the repository root:

```sh
python3 -m venv evals/.venv
evals/.venv/bin/pip install -r evals/requirements.txt
evals/.venv/bin/python evals/test_runner.py
evals/.venv/bin/python evals/run.py
```

The default run exercises all classification, normalization, and workflow items
against application code. Workflow tests use the real LangGraph with controlled
MCP responses and injected faults, not a live transport. Alias regressions fail
the run rather than being relabeled. The glucose parenthetical alias regression
is now fixed in the application and protected by classification tests.

Paid model experiments are explicit. The runner reads the existing backend `.env`:

```sh
EVAL_JUDGE_MODEL=qwen/qwen3-30b-a3b-instruct-2507 \
  evals/.venv/bin/python evals/run.py --judge --datasets judge_calibration
EVAL_JUDGE_MODEL=qwen/qwen3-30b-a3b-instruct-2507 \
  evals/.venv/bin/python evals/run.py --judge --datasets explanations chat
evals/.venv/bin/python evals/run.py --datasets extraction
```

Use `--limit 1` for smoke tests. Extraction itself uses the application's model,
even without a judge. Run classification/normalization/workflow for a free suite.
The explicit judge model prevents accidental defaults to another provider.
Judge thresholds are provisional; run all calibration anchors before promoting
a judge to a release gate. A two-case connectivity smoke test is not calibration.

To target a case, pass `--case ID` (repeat for multiple IDs), for example
`--case judge-missing-pass --case judge-missing-fail` with the judge-calibration
command. Calibration uses explicit evaluation steps so the model does not invent
conflicting completeness requirements while generating its own rubric steps.

The local OpenRouter adapter explicitly closes per-call clients before their
event loops exit (a cleanup workaround for DeepEval 4.3.0). Its tests cover both
successful and failed requests. Expected malformed-PDF warnings are silenced only
while validating that negative fixture. The console prints executed, passed,
error and skipped counts and the IDs of failed cases; `ok` means execution
succeeded, not that the metrics passed.

## Implemented metrics and reports

- Real application-schema JSON correctness with DeepEval; generation schema is
  checked after the app's parsing/repair, not asserted to be raw JSON compliance.
- Exact row precision/recall and complete-report agreement, preserving duplicate
  counts, numeric formatting equivalence, units and qualifiers.
- Exact classification and unit/alias checks; workflow outcomes, routing, row
  identity, per-row order, faults, and required calls with DeepEval argument checks.
- DeepEval faithfulness, answer relevancy, source-fact G-Eval, conversational turn
  faithfulness, contextual relevancy for recorded retrieval output, and judge
  verdict agreement against calibration anchors.

Deterministic DeepEval metrics use a non-network model that raises if invoked.
An evaluator error has a null score; it is never converted to a quality zero or
a successful result. Application fallback text is flagged separately. Each report
records run ID, dataset manifest hash, judge/version, per-item duration, actual
outputs, scores, thresholds, errors, skipped cases and failed item IDs.
Reports default to ignored `evals/results/latest.json`. Exit 1 means failed metrics
or execution errors; exit 2 means incomplete/skipped coverage; exit 0 means the
requested slice passed. A limited run does not imply the entire suite passed.

## Recorded output and Langfuse

Use `--predictions file.jsonl` to evaluate actual captured component outputs.
Each line is `{dataset, id, actual, trace_id?, observation_id?}`. `actual` matches
the adapter's JSON shape (`actual_output` for prose; `labs`/`outcome` for extraction;
`response`/`nodes`/`tools_called` for workflows). Retrieval predictions contain
`relevant_evidence_ids` and `actual_output`; candidate snippets come from the
golden case. Missing selected predictions cause errors. Do not substitute gold
labels for actual application output.

```sh
evals/.venv/bin/python evals/run.py --datasets workflow \
  --predictions actual-workflows.jsonl --publish
```

Publishing attaches numerical scores to the provided real trace/observation IDs
using Langfuse 5.0.1 and flushes on completion. It requires recorded IDs; offline
subprocess adapters disable their own tracing for deterministic isolated runs.
This does not change tracing in the running application. No live dataset upload
or scheduled production evaluator is enabled by this command.

## Remaining integration scope

There is no fabricated retriever execution: retrieval requires actual predictions.
Chat cases currently exercise the responder with report/history context; WebSocket
checkpoint persistence and interleaved-session transport tests remain separate.
MCP transport-specific judging/native trajectory metrics, raw-generation scoring,
live dataset experiments, asynchronous online sampling and an automatic trace
export adapter are not implemented here. This first offline runner accepts all
eight dataset categories but does not claim every category was run against live
models. Clinical judgment remains excluded from the high-confidence dataset.
