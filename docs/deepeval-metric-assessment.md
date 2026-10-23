# DeepEval assessment for the lab analyzer

16 October 2026. Documentation research and proposal; DeepEval has not been
installed, and no evaluators or live scoring jobs were created.

## Recommendation

Use DeepEval as an evaluation engine alongside Langfuse. Reuse its built-in
metrics where their contracts match our task. Keep exact clinical data checks
and software behavior tests in Python. Generic language judges cannot establish
that a lab value, unit conversion, or severity threshold is correct.

## Built-in metrics and application fit

| Metric | Technique and required evidence | Application and priority |
| --- | --- | --- |
| [JsonCorrectnessMetric](https://deepeval.com/docs/metrics-json-correctness) | Deterministic validation against a Pydantic schema. Disable generated failure reasons to avoid judge calls. | First: extraction response structure. Score raw response and repaired/validated result separately. Valid JSON can still contain wrong values or missing rows. |
| [ToolCorrectnessMetric](https://deepeval.com/docs/metrics-tool-correctness) | Compare actual calls with expected calls; configure argument checking and ordering explicitly. Supplying available tools additionally enables judge-based optimality assessment. | First: graph-to-MCP expected tool calls and exact numeric arguments. Omit available-tools judging for deterministic gates. Check ordering within a row or dependency branch, not a single global order across concurrent rows. |
| [ContextualRelevancyMetric](https://deepeval.com/docs/metrics-contextual-relevancy) | Judge retrieved content against the task; needs actual retrieval context. | First: whether PubMed/web evidence addresses the abnormal analyte and question. Does not establish source quality or medical correctness. |
| [FaithfulnessMetric](https://deepeval.com/docs/metrics-faithfulness) | Judge generated claims against supplied retrieval context. | First: explanation and next-step grounding. Supply the actual evidence and clearly labeled report facts. Pilot ambiguous-claim penalties; a noncontradicted claim is not necessarily supported. |
| [AnswerRelevancyMetric](https://deepeval.com/docs/metrics-answer-relevancy) | Judge whether the answer addresses its input. | First: explanation relevance and single-turn chat relevance. A relevant answer can still be wrong. |
| [TurnFaithfulnessMetric](https://deepeval.com/docs/metrics-turn-faithfulness) | Judge conversation turns against context available on each turn. | First chat suite: consistency with the report and actual supplied evidence. Chat does not currently perform fresh retrieval on every turn. |
| [KnowledgeRetentionMetric](https://deepeval.com/docs/metrics-knowledge-retention) | Judge retention of facts provided by the user across turns. | Later chat suite: follow-up history. Not automatically a check of persisted PDF facts; do not reward accepting an incorrect user assertion over report ground truth. |
| [ConversationCompletenessMetric](https://deepeval.com/docs/metrics-conversation-completeness) | Judge whether user intentions were addressed across a conversation. | Later: unanswered follow-ups and partial answers. Complement with exact report-fact assertions. |
| [ContextualPrecisionMetric](https://deepeval.com/docs/metrics-contextual-precision) | Judge ranking of relevant retrieved nodes using an expected answer. | Later offline: retrieval ranking with reviewed reference answers. Its rank-sensitive score is not plain precision at k. |
| [ContextualRecallMetric](https://deepeval.com/docs/metrics-contextual-recall) | Judge how much of an expected answer is attributable to retrieved context. | Later offline: coverage of required evidence. Not recall across all relevant medical literature. |
| [ArgumentCorrectnessMetric](https://deepeval.com/docs/metrics-argument-correctness) | Judge whether tool arguments fit the task, without expected calls. | Advisory when exact expected arguments are unavailable. Prefer deterministic argument comparison for lab values and units. |
| [MCPUseMetric](https://deepeval.com/docs/metrics-mcp-use) | Judge actual MCP tools/resources/prompts and arguments against available server capabilities and the task. | Pilot: assess use of our real clinical MCP tools. Requires server definitions and actual recorded calls; it does not test transport, propagation, timeout handling, or arithmetic. |
| [MultiTurnMCPUseMetric](https://deepeval.com/docs/metrics-multi-turn-mcp-use) | Conversation-level MCP usage judgment. | Defer until we have conversations that actually invoke MCP across turns; do not manufacture calls for report-context-only chat. |
| [MCPTaskCompletionMetric](https://deepeval.com/docs/metrics-mcp-task-completion) | Conversation-level assessment of task completion with MCP activity. | Later for suitable multi-turn MCP scenarios. Still requires independent checks of final data and side effects. |
| [TaskCompletionMetric](https://deepeval.com/docs/metrics-task-completion) | Judge task and observed outcome from execution evidence. | Advisory end-to-end measure; never sufficient for clinical-data release gates. Verify supported tracing/test-case input contract in the pinned version. |
| [StepEfficiencyMetric](https://deepeval.com/docs/metrics-step-efficiency) | Native trajectory-based judge; requires DeepEval tracing rather than standalone measure. | Defer: our workflow is prescribed by LangGraph. Deterministic call counts, retry budgets, latency, and cost are more directly actionable initially. |

PlanQuality and PlanAdherence are a poor initial fit because this application
does not ask an LLM to generate an execution plan. A code-defined LangGraph
needs branch, dependency, termination, and recovery assertions.

## Custom checks we still need

- Row precision/recall and complete-report accuracy against labeled fixtures.
- Exact analyte identity, decimal, qualifier, unit, and reference-range matching.
- Numeric conversion and boundary tests; missing and conflicting range handling.
- Severity agreement and critical-case precision/recall using reviewed labels.
- Alias invariance, for example equivalent glucose names yielding consistent
  rule selection. This checks software consistency, not clinical validity.
- Conditional routing, partial-failure recovery, retry limits, cancellation,
  session isolation, and report persistence.
- Citation-to-claim matching and source quality where required; a generic
  faithfulness score alone does not prove either.

[G-Eval](https://deepeval.com/docs/metrics-llm-evals) supplies a framework for our
custom explanation, next-step, uncertainty, and scope rubrics. It is not a
prevalidated clinical evaluator. Calibrate each rubric against reviewed good
and bad examples and track false passes and false failures.

[DAGMetric](https://deepeval.com/docs/metrics-dag) can express a branching rubric.
Its score mapping can be deterministic while its LLM judgments remain variable.
Use Python assertions for hard facts before any qualitative judge.

## Coverage and execution

| Test layer | Application coverage | Proposed method |
| --- | --- | --- |
| Unit | Parsing, normalization, unit conversion, thresholds, routing predicates | Fast deterministic Python tests; schema metric only where useful. |
| Component | Extractor, retriever, explainer, next-step generator, chat responder | Isolated fixtures plus the relevant DeepEval metrics above. Distinguish live-model evaluations from ordinary unit tests. |
| Pairwise integration | Extractor-to-schema, translator-to-classifier, retrieval-to-explanation, graph-to-MCP, analysis-to-chat | Contract assertions, expected tool calls/arguments, frozen evidence, and output grounding. |
| Workflow | Critical and noncritical branches, concurrent rows, retries and fallback | Trajectory invariants and injected failures; selected judge diagnostics. |
| End to end | Upload synthetic PDF, analyze, render report, ask follow-ups, reload report | Exact expected facts plus answer/turn faithfulness, relevance, task success, latency and cost. |

DeepEval supports [pytest-style evaluation](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)
and [component-level observation](https://deepeval.com/docs/evaluation-component-level-llm-evals).
These are execution mechanisms; test coverage still depends on our fixtures,
assertions, and failure scenarios.

## Langfuse and OpenRouter integration

1. Keep existing Langfuse tracing and its dataset/experiment records.
2. Map actual component inputs, outputs, evidence, expected results, and MCP
   calls into DeepEval test cases. Preserve trace, observation, row, and session IDs.
3. Run standalone metrics offline first. Write score, reason, evaluator version,
   judge model, and evaluation status back to the corresponding Langfuse record.
   A judge failure is an evaluation error, not a score of zero.
4. Do not assume native DeepEval trajectory metrics can consume Langfuse traces
   automatically. Assess a supported adapter or use an isolated native tracing
   harness before adopting metrics requiring DeepEval's own trajectory format.
5. Use the documented [OpenRouterModel](https://deepeval.com/integrations/models/openrouter)
   with the existing OPENROUTER_API_KEY and an explicitly selected judge model.
   No extra provider key is needed for this route. Verify structured output and
   judge agreement before choosing a cheap model; keep judge configuration
   separate from the application model under test.
6. Pin the DeepEval release and metric configuration during implementation.
   Lock evaluation mode, prompts/rubrics, dataset, judge model, and thresholds
   for comparisons. Do not introduce another evaluation service for the first suite.

Initial delivery should include the five first-priority component metrics,
TurnFaithfulness for chat, exact tool checks, and our deterministic lab metrics.
Pilot MCPUse separately. Add reference-answer retrieval metrics and broader
conversation judges once reviewed datasets exist. Add asynchronous production
sampling only after offline calibration; do not run every judge on every request.
