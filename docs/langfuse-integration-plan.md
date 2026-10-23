# Langfuse integration plan

Prepared 16 October 2026. Core tracing from phase 1 is now implemented and live.
Prompt management, datasets/evaluators, feedback, and CI remain subsequent work.

Verified with the complete 15-row sample PDF, then a smaller synthetic PDF and
two follow-up turns after the final context fix. The final session exported 51
observations across three distinct traces, including six generations with token
usage and a total reported model cost of $0.00028842. The audit found no missing
parents, unfinished exported observations, or unexpected input/output content in
metadata mode. The analyzer suite passed 129 tests; dependency checks passed.

[Verified analysis trace](https://cloud.langfuse.com/project/cmv9z950s00liad0ejyo2hk7o/traces/de98beedc69ddd30094c3e6d7b401ec4)

Implemented: request and per-turn session correlation, graph callbacks, per-call
W3C MCP propagation, worker-thread context isolation, tool/retrieval observations,
OpenRouter generation usage/cost, retries/fallback outcomes, export masking,
shutdown flushing, configuration documentation, and local OTLP integration tests.
The root CSV log still has its original schema; CSV trace-ID correlation and
stored-report service propagation remain follow-up items within the wider plan.

## Outcome and scope

Make each lab analysis and follow-up answer inspectable from request to model
response, including extraction, validation, MCP tools, retrieval, retries,
fallbacks, latency, tokens, cost, prompt versions, evaluations, and feedback.
Keep vision and email outside this rollout. Keep the deterministic classifiers
and reference dictionaries in code.

Initial deployment recommendation: Langfuse Cloud for synthetic development
data, with a development project separate from any later production project.
Self-hosting is an alternative infrastructure decision; it does not share the
application's auth or patient databases. Choose the deployment and data region
before enabling exports of real reports.

## Current repository findings

- `app/routers/labs.py` accepts PDFs and manual lab rows. PDF extraction occurs
  before `agent.analyze_labs()` creates its eight-character run/thread ID.
  Start request tracing before extraction so rejected PDFs are represented.
- `app/pdf_extract.py` reads text locally, truncates the extraction prompt to
  12,000 characters, calls the model, validates JSON, and retries invalid output.
- `app/graph.py` implements validate, translate, check_units, classify, route,
  critical_alert, explain, aggregate, and an interrupt-based chat node.
- `app/mcp_client.py` talks to one shared stdio subprocess. `app/mcp_server.py`
  executes tool bodies in AnyIO worker threads. Most model calls happen here,
  beyond LangGraph's automatic callback visibility.
- `app/llm.py` centralizes provider dispatch and application retries. Provider
  failures are logged and often returned as `None`; HTTP 200 can therefore
  contain degraded results. Also account for provider SDK internal retries.
- `app/routers/chat.py` resumes the graph for each WebSocket question. Chat
  checkpoint state is process-local and disappears on restart.
- The frontend directly calls the analyzer without authenticated identity.
  PatientService does authenticate users and calls the analyzer for saved reports.
- The run CSV has a separate request ID, and detailed response statistics are
  currently collected only for `/analyze_labs`, not `/analyze_report`.
- Existing fixtures: one synthetic PDF and three mixed CSV panels. Existing
  tests cover classification, unit conversion, ranges, and schemas. No CI
  workflow exists in this checkout.

## SDK and configuration

Plan to pin `langfuse==5.0.1`, the latest PyPI release verified during this
planning session. SDK v5 requires Python >=3.11 and Langfuse Cloud or self-hosted
server >=4.59.0. The running environment has Python 3.13, langchain-core 1.6.11,
LangGraph 1.2.15, MCP 1.30.0, and OpenAI 3.31.0. Lock the tested dependency set
during implementation; the repository currently has broad lower bounds.

SDK configuration in the ignored backend `.env`:

```dotenv
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=
LANGFUSE_TRACING_ENVIRONMENT=development
```

Proposed application settings, to be implemented rather than assumed built in:

```dotenv
OBSERVABILITY_ENABLED=true
OBSERVABILITY_CONTENT_MODE=metadata
PROMPT_SOURCE=local
PROMPT_LABEL=production
EVALUATION_ENABLED=false
```

Load environment variables before creating the SDK clients, in both analyzer
and MCP processes. Create one client/exporter per process. Batch exports; flush
on shutdown and on one-shot experiment exit, not after every tool call. SDK
failure, invalid credentials, or a Langfuse outage must not prevent analysis.
Do not pass Langfuse secrets to the frontend or unrelated Java services.

## Phase 1: connected traces and accurate accounting

Add a shared `app/observability.py` with initialization, explicit capture rules,
metadata helpers, redaction, context propagation, and a disabled/no-op path.

Trace scope:

- One `analyze-report` root per PDF request, including upload rejection,
  extraction, and analysis; one `analyze-labs` root per manual request.
- One new `answer-followup` trace per accepted chat question.
- One full UUID session identifier per initial analysis and its follow-up turns.
  Preserve the existing thread ID contract and maintain an explicit mapping.
  Use native 32-hex trace IDs, not the existing eight-character run IDs.
- End the initial trace when the graph parks for chat. Do not measure idle time
  between questions or the whole WebSocket lifetime as inference latency.

Expected trace structure (stable names, dynamic row IDs in metadata):

```text
analyze-report
  read-pdf
  extract-lab-rows
    generate-extraction             generation, each actual model request
    validate-extraction             span, each schema validation attempt
  analyze-labs                      LangGraph workflow
    validate-records
    translate-fields
      translate-to-english          MCP tool
        generate-translation        generation
    check-units
    classify-results
      classify-lab-result           MCP tool
      lookup-reference-range        conditional MCP tool + generation
    route-results
    flag-critical-results           conditional
    explain-results
      explain-result                span per row, up to 4 concurrent
        retrieve-clinical-context   retriever
          search-pubmed
          search-web                conditional fallback
        generate-explanation        generation
        generate-next-steps         conditional generation
    aggregate-results
```

Use the Langfuse LangChain callback for graph execution and the Langfuse OpenAI
wrapper for OpenRouter requests. Add manual spans only for uncovered semantic
steps. Establish ownership of observations so the same model call is never
counted by both callback and wrapper. Leave OpenRouter Broadcast disabled for
this project to avoid another copy of each generation.

For each MCP invocation, inject W3C trace context through `call_tool(...,
meta=...)`; extract `_meta` server-side and attach/detach context around execution.
MCP 1.30.0 in this environment exposes the required `meta` argument. Propagate
the allowed session/environment attributes too. Never store active request
context in a process global or permanently in the shared subprocess environment.
Verify context reaches AnyIO workers and stays isolated across concurrent rows
and simultaneous requests. Context must be propagated per call.

Generation data: requested and returned model, provider when supplied, operation,
prompt version, parameters, input/output tokens, cache/reasoning token counts
when returned, finish reason, response ID, status, and duration. Preserve usage
instead of discarding it when returning `message.content`. Record every explicit
provider attempt; either disable SDK internal retries and own the retry policy,
or make their aggregate timing/attempt visibility explicit. Do not claim to see
individual hidden HTTP retries if the chosen wrapper does not expose them.

Prefer actual cost returned by OpenRouter when available. Otherwise match the
model to Langfuse pricing or use versioned explicit rates. Mark unavailable cost
as unknown, never zero. Separate generation, experiment, and judge spending.

Record outcomes beyond HTTP status: extraction failure, schema retry, truncated
input, empty completion, rate limit, provider fallback, translation fallback,
rejected unit, unknown range, retrieval with no results, and rule-based output.
Attach run-level counts and per-row origins: report range, curated dictionary,
or LLM lookup. Flag degraded successful requests as warnings.

Return optional trace/session identifiers in API responses and correlate them
with existing run logs. Populate response fields explicitly because FastAPI's
response model would otherwise remove undeclared fields. Cover both endpoints.

Acceptance: a synthetic PDF and manual panel produce correctly nested, complete
traces; two simultaneous analyses do not mix parents; tokens/cost are not
duplicated; extraction errors and degraded responses are visible; export outage
does not break requests; two follow-up turns produce separate session-linked
traces. Fetch exported observations through the Langfuse CLI and audit them
against the current best-practices page before considering this phase complete.

## Phase 2: prompt management with reproducible rollback

Inventory and migrate these existing prompt families:

| Prompt | Current location | Dynamic variables |
|---|---|---|
| `labs/extract-report` | `pdf_extract.py` | report_text, validation_feedback |
| `labs/translate-fields` | `mcp_server.py` | numbered_fields |
| `labs/lookup-reference-range` | `mcp_server.py` | test_name, value, unit |
| `labs/explain-result` | `mcp_server.py` | test_name, value, unit, status, reference_range, context |
| `labs/suggest-next-steps` | `mcp_server.py` | same fields plus explanation |
| `labs/answer-followup` | `mcp_server.py` | question, results_json, history |

Use chat prompts where a system/user separation exists. Convert interpolation
to Langfuse `{{variables}}`, keeping conditional string construction in code.
Start with exact existing text and current behavior. Link the resolved prompt
object/version to each generation. Cache prompts; use checked-in local fallback
templates and record fallback use. Pin resolved versions for a complete run so
a label move cannot change prompts halfway through a report. Roll back labels
to a tested version or set `PROMPT_SOURCE=local`.

Keep model/temperature/output budget in versioned experiment configuration.
Do not move rule-based severity boundaries or clinical reference dictionaries
into editable prompts. Prompt migration is complete when compiled messages match
the old templates and every generation links to the intended prompt version.

## Phase 3: datasets, evaluation, and model selection

Use the synthetic PDF and CSVs as seeds, not as a sufficient benchmark. Build
versioned extraction, analysis, and follow-up datasets with hand-reviewed
expected values, units, ranges, classifications, and supportable answer facts.
Generate variants for boundary values, missing ranges, qualitative values,
non-English terms, incompatible units, malformed documents, and prompt-injection
text inside reports. Include multi-page/long reports to test the 12k cutoff.
Split tuning and held-out sets by originating report/template to prevent leakage.
Clinically consequential labels need qualified review; software fixtures alone
do not establish clinical correctness.

Evaluation layers:

| Layer | Proposed measures | Execution |
|---|---|---|
| Extraction | valid JSON, field exact match, row precision/recall, omitted/invented numeric values | Deterministic against expected rows |
| Rules | unit conversion accuracy, severity agreement, critical-result recall, qualitative agreement | Existing tests + dataset evaluator |
| Retrieval | retrieval success, valid source URLs, support in retrieved text | Code checks + reviewed samples |
| Explanations | faithfulness to supplied results/context, relevant next step, unsupported claims | Calibrated judge + human review |
| Chat | numerical consistency, supported claims, handling missing information | Code checks + calibrated judge |
| Operations | p50/p95 latency, tokens/cost per report, retries, fallback/unknown rates | Trace-derived metrics |

A reachable citation does not prove an explanation is supported. Score source
support against content actually retrieved. Do not label an LLM judge score as
medical accuracy. Calibrate judges against human labels and keep human review
for disagreements. Run judges asynchronously on selected synthetic or approved
examples; their latency must not delay the user's analysis.

Baseline the current Qwen model. Compare additional budget Qwen/DeepSeek models
only after verifying current availability/pricing. Fix dataset, prompt versions,
concurrency, and budgets across candidates; repeat stochastic cases and show
per-case failures. Choose by extraction quality and critical-result preservation
first, then cost and latency. No silent automatic model promotion.

## Phase 4: feedback and stored-report correlation

Proposed signals, all currently unimplemented:

| Priority | Status | Signal | Meaning and limits | Effort | Implementation |
|---|---|---|---|---|---|
| P0 | Proposed | extraction_schema_valid, fallback_used | Structural/runtime facts, not clinical quality | S | App code; Langfuse code evaluator also possible |
| P1 | Proposed | user_rating | User-reported usefulness, affected by selection bias | M | Result/answer UI -> authenticated backend -> score |
| P1 | Proposed | issue_reported | User-selected wrong value, range, explanation, or citation; unverified until reviewed | M | Backend score + annotation |
| P2 | Deferred | clinician_correction_submitted | Useful labeled correction, requires reviewer identity and correction workflow | L | New workflow + annotation/dataset review |

Choose the feedback UI before implementing it. Suggested first version:
thumbs up/down on a result or chat answer, with an optional issue category.
Attach feedback to the specific row observation or chat generation, not just
the whole report. Use stable server-issued result IDs, score IDs for idempotency,
and rate limits. Never expose Langfuse keys to the browser.

The current analyzer has no verified user authentication or session ownership.
Add authenticated feedback and ownership validation before accepting user/trace
associations. Derive user attribution only from verified JWT identity or a
trusted backend, never an arbitrary browser-supplied user header. Anonymous
development requests remain anonymous.

Propagate W3C trace context or a request correlation ID through patientService's
AnalyzerClient for stored reports. Preserve trace/session IDs in the analysis
payload and through reload/reanalysis; new runs get new IDs. Link application
records to telemetry without turning telemetry into the medical record store.
Avoid instrumenting unrelated auth queries or passwords into Langfuse.

## Phase 5: monitoring and regression gates

Create views by environment, release, operation, model, and prompt version.
Monitor failures, degraded success, empty/truncated extraction, unknown ranges,
retrieval misses, p95 latency, spend per report, and fallback/provider rates.
Establish a baseline before setting operational thresholds. Alert only on
actionable changes and distinguish export failures from analysis failures.

Introduce CI in two levels: fast deterministic tests on every change; budgeted
Langfuse dataset experiments on an explicit trusted trigger. The repository
currently has no `.github/workflows`. Evaluate the official
`langfuse/experiment-action` against the chosen CI setup before adding it.
Agree triggers, evaluator set, model budget, and regression thresholds with the
user before implementation. Never run secret-bearing workflows on untrusted
fork code. Proposed hard fixture checks: no altered source numbers and no missed
expected critical cases. These are dataset checks, not production guarantees.
Keep latency/cost advisory until sufficient repeated runs establish variability.
Store dataset version, prompts, model settings, evaluator version, and commit
with every experiment. Require reviewed evidence before promotion.

## Data capture and operational boundaries

Default to allowlisted operational metadata. Full prompt/completion and graph
state capture is permitted only in an explicit synthetic-data mode or with an
approved data handling policy. Suppress raw PDFs, names, DOB, report identifiers,
filenames, paths, email addresses, tokens, keys, and connection strings. Free-text
prompts and outputs can reintroduce identifiers; key-name masking alone is
insufficient. Pseudonymized medical data remains sensitive. Mask at export and
test every producer, including graph callbacks, model wrappers, tool exceptions,
and the MCP subprocess. Make the reduced evaluation visibility in metadata-only
mode explicit; use synthetic datasets for content-based debugging initially.

Configure access, region, retention, and deletion for the chosen deployment.
Do not create public trace links for patient data. Langfuse ingestion must not
block report completion, and losing telemetry must be observable locally.

## Delivery sequence

1. Connected tracing + MCP context + OpenRouter accounting + content controls.
2. Prompt versions and cached local fallbacks.
3. Synthetic datasets, deterministic scoring, and model experiments.
4. Authenticated feedback and persisted report correlation.
5. Dashboards, calibrated judges, and CI regression gates.

Each delivery should include integration tests, a verified exported example,
and rollback via feature flags. No change to VLM or email is required.

## Sources checked

- [SDK release](https://pypi.org/project/langfuse/5.0.1/)
- [SDK v5 compatibility](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v4-to-v5)
- [Trace best practices](https://langfuse.com/docs/observability/best-practices)
- [LangGraph integration](https://langfuse.com/integrations/frameworks/langgraph)
- [MCP context propagation](https://langfuse.com/docs/observability/features/mcp-tracing)
- [OpenRouter integration](https://langfuse.com/integrations/gateways/openrouter)
- [Masking](https://langfuse.com/docs/observability/features/masking)
- [Prompt availability](https://langfuse.com/docs/prompt-management/features/guaranteed-availability)
- [Dataset experiments](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [CI experiments](https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd)
- [Feedback signals](https://langfuse.com/academy/monitoring/capturing-signals)
