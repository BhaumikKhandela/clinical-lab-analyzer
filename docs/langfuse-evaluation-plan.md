# Deep evaluation plan for the Clinical Lab Result Analyzer

16 October 2026. Evaluation architecture proposal. A local synthetic dataset
set now exists in `evals/golden/v2/`; no live datasets, evaluators, scores, or automated
rules were created. The running application and full synthetic trace capture
configuration are unchanged.

The active [high-confidence dataset](../evals/golden/v2/README.md) contains
67 machine-verified software cases across all eight categories. Clinical advice
and patient-severity labels are excluded following the user's request to avoid
human-review dependencies. The earlier v1 is historical draft material only.

The [DeepEval metric assessment](deepeval-metric-assessment.md) maps documented
built-in metrics to this pipeline, including MCP and conversation evaluation.
Proposed implementation: DeepEval supplies reusable judges and selected
deterministic metrics; Langfuse remains the experiment and trace record.

## Decisions this evaluation system should support

1. Can a new model/prompt extract the complete report without changing values,
   units, qualifiers, or reference ranges?
2. Do normalization, units, and severity rules behave consistently and agree
   with independently reviewed expected classifications?
3. Are explanations and next steps supported by the actual report and retrieved
   evidence, and does chat stay consistent with that report?
4. Can we reduce cost and latency without regressing on those properties?

Start with offline benchmark experiments, then add asynchronous monitoring of
live traces. Use deterministic checks for facts and arithmetic; use calibrated
judges and human review for interpretation. Do not collapse these into one
opaque "quality" score.

## Evidence from this application

- Langfuse dataset listing returned zero datasets, and score-config listing
  returned zero score definitions at planning time.
- The repository contains one 15-row synthetic PDF, three mixed CSV panels,
  and 129 passing tests, including tracing tests. These provide seeds and
  regression coverage, not an independent clinical benchmark.
- Full synthetic traces now contain model messages and outputs across PDF
  extraction, translation, MCP tools, retrieval, explanations, and chat.
- Extraction truncates input at 12,000 characters and can retry malformed JSON.
  First-attempt and final-attempt success must be measured separately.
- A concrete normalization inconsistency was reproduced without an LLM:
  `Glucose`, `Fasting glucose`, and `Glucose (Fasting)` at 118 mg/dL with printed
  bounds 70–99 return Warning, Warning, and Critical respectively. The third
  spelling misses a curated alias and uses derived critical thresholds. This
  is evidence of inconsistent software behavior; it is not a clinical verdict.
- Translation stores `test_name_en`, but classification uses `test_name`.
  Evaluations must exercise the real path rather than assuming the translated
  name is the classifier input.
- For unfamiliar tests, the LLM can supply both reference and critical bounds.
  Mathematical validation of those bounds does not establish clinical validity.
- Retrieval supplies abstracts/snippets to explanations, and can fall back to
  web search. A real URL is not proof that the cited text supports a claim.
- HTTP success can include rule-based fallback, missing evidence, or row errors.
  A completed request is not automatically a correct analysis.
- The graph chooses workflow/tool order in code. Evaluate branch contracts and
  tool arguments; an autonomous-agent tool-choice metric would misdescribe it.

## Metric set for review

P0: proposed hard regression checks on reviewed fixtures. P1: measured quality
improvements and review signals. P2: operational optimization. Existing means
there is already code/test/trace support, not that a Langfuse score exists.

| Priority | Status | Metric | Source/evidence | Decision informed | Measurability |
|---|---|---|---|---|---|
| P0 | New score; schema validation exists | `extraction_schema_valid` | Raw generation, parsed extraction, retry outcomes | Reject unusable model/prompt changes | Boolean per attempt; final success separately |
| P0 | New | `extraction_value_exact_match`, `extraction_unit_match`, `extraction_range_match` | Source PDF/text + independently transcribed rows | Block altered facts | Row/field comparison; preserve qualifiers and printed strings |
| P0 | New | `extraction_row_precision`, `extraction_row_recall`, `report_all_rows_correct` | Reviewed source row inventory | Detect inventions, omissions, duplicates and row swaps | One-to-one matching; precision/recall and report Boolean |
| P0 | Partial unit tests; new dataset score | `normalization_invariant`, `unit_conversion_correct` | Reproduced alias inconsistency; unit tests | Block spelling/translation/unit-dependent regressions | Equivalent-input pairs and hand-calculated conversions |
| P0 | Partial unit tests; new independent labels | `severity_agreement`, `critical_recall`, `critical_precision` | Reviewed policy labels; classifier output | Block missed critical fixtures and track over-alerting | Confusion matrix; raw TP/FN/FP denominators |
| P0 | New | `report_facts_preserved` | Explanation/chat vs authoritative source facts | Block changed numbers or patient/report mixing | Code checks where facts are structured; judge flags plus human review otherwise |
| P0 | New | `unsupported_context_handled`, `injection_resisted` | Missing-context and report-instruction fixtures | Block invented personalization or altered workflow | Reviewed required/forbidden behaviors; code + adversarial review |
| P1 | New | `reference_range_supported` | Printed range, curated policy provenance, or lookup evidence | Review unreliable model-generated ranges | Code checks for origin/preservation; expert review for validity |
| P1 | New | `retrieval_relevance`, `claim_source_support` | Exact retrieved snippets and claims | Improve retrieval and grounding | Code for source presence; calibrated judge/human for relevance and support |
| P1 | New | `explanation_consistent`, `next_step_supported` | Lab facts, classification, evidence, applicable context | Improve prose without hiding upstream errors | Separate Boolean rubrics; domain-qualified review for appropriateness |
| P1 | New | `chat_answer_supported`, `chat_question_addressed` | Full turn history + source report + question | Improve follow-up reliability | Numerical checks + calibrated judge; missing-information cases |
| P1 | Existing trace signals; new aggregations | `fallback_used`, `retrieval_empty`, `row_error_count` | MCP outcomes, API errors, trace levels | Investigate degraded successful requests | Code-derived; score/aggregate without claiming accuracy |
| P2 | Existing trace signals | Latency, actual generation cost, retry count, judge cost | Trace usage/timing | Choose an economical passing candidate | Per stage/report, distribution and cost per fully correct report |

No generic toxicity, sentiment, or stylistic similarity score in v0. Add a metric
when an observed failure or explicit requirement gives it a decision to change.

## Scoring definitions and limits

### Extraction

Match source rows to predictions one-to-one using reviewed canonical test IDs,
specimen/date/panel context, and occurrence IDs. Do not match rows solely on the
model's chosen name or overwrite duplicates in a dictionary. Penalize extra,
omitted, duplicated, and misassigned rows. Separate extraction from normalization:
an equivalent synonym may pass test identity while an altered numeric value fails.

Compare numeric values with Decimal and explicit source precision rules; never
use a broad tolerance that masks decimal shifts. Preserve reported strings and
qualifiers (`<`, `>`, negative, trace, graded positives) alongside normalized
values. Approved unit conversions are a downstream score, not a license for the
extractor to silently rewrite source facts. Missing reference fields remain null.

Report row-weighted metrics and report-weighted all-correct rates. A 40-row panel
must not hide failures on a small panel. A schema failure or timeout counts as a
failed report in the end-to-end denominator rather than disappearing from it.

### Classification

Maintain two explicit tracks: agreement with an approved software policy, and
agreement with independently reviewed clinical labels. Neither the current code,
CSV `Status` values, nor the app's own prose can be copied automatically as gold.
Record review status, policy source/version, units and applicable context.

Test exact bounds and just-inside/outside values; unknown tests; report vs curated
range precedence; incompatible units; alias/paraphrase invariance; and qualitative
findings. Track both false negatives and false positives for critical labels.
Unsupported comparisons must yield an explicit unknown/error according to the
approved policy, not a guessed severity. Age/sex/pregnancy-specific interpretation
requires context the analyzer currently does not consume; test honest handling of
missing context rather than pretending to support personalized ranges.

### Grounding, explanations, next steps, and chat

Score factual consistency separately from evidence support and action quality.
An explanation may faithfully justify an incorrect upstream classification, so
it cannot rescue a failed classification score. A numeric mismatch in a sentence
can be detected in structured cases; arbitrary prose requires careful entity
alignment rather than checking whether every number occurs somewhere in context.

Give the judge the exact lab facts, evidence snippets, and conversation that the
model saw. Ask for pass/fail or explicit not-applicable, a short reason, and the
offending claim/evidence references. Absence of evidence is not scored as fully
grounded. Source presence/HTTP reachability and claim support remain different
checks. Code tests cannot establish that a treatment or follow-up is appropriate;
that rubric needs domain-qualified review.

For chat, include follow-ups referring to previous turns, questions about values
absent from the report, contradictory user assertions, and concurrent sessions
with different numbers. No information from one session may appear in another.

## Dataset proposal

Begin with a reviewable v0 of 10 scenario families, then expand after reviewing
results. This is deliberately a wiring/smoke benchmark, not a reliable estimate
of general performance. Final population metrics require a larger representative
held-out set; rare critical cases should also have an enriched diagnostic slice.

| Family | Source mix | Intended coverage |
|---|---|---|
| Complete mixed panel | Existing synthetic PDF, manually transcribed | End-to-end extraction and row accounting |
| Normal panel | Small generated PDF | Normal explanations; unnecessary follow-up behavior |
| Critical/near-boundary panel | Expert/policy-reviewed synthetic rows | False negatives and boundary inclusivity |
| Alias pair | Confirmed glucose naming inconsistency | Equivalent spelling gives equivalent behavior |
| Equivalent-unit pair | Reviewed conversion worksheet | Unit reconciliation and incompatible-unit rejection |
| Qualitative/qualified results | Synthetic negative, graded and less-than values | Preserve meaning; explicit unsupported cases |
| Missing/conflicting ranges | Synthetic report text | Source precedence and uncertainty |
| Long/invalid/scanned document | Generated fixtures | Truncation disclosure; correct failure behavior |
| Evidence plus injected instructions | Frozen snippets and adversarial report text | Grounding and resistance to report-as-instruction |
| Multi-turn/two-session chat | Reviewed questions over different panels | Missing facts, consistency and session isolation |

One family may contain paired variants and multiple task-specific items. Keep
canonical fixtures in the repo, with file hashes, generator seeds, and no machine-
specific absolute paths. Host reviewed task items in Langfuse datasets named
`labs/extraction`, `labs/classification`, `labs/explanations`, and `labs/chat`.
Use stage and end-to-end tests over overlapping fixture IDs without treating
them as independent statistical samples. Define a separate calibration dataset
for each LLM judge.

Proposed item responsibilities:

```json
{
  "input": {
    "task": "extract-report",
    "fixture_id": "mixed-panel-v1"
  },
  "expected_output": {
    "labs": [
      {"row_id": "r1", "test_id": "hemoglobin", "reported_result": "14.2",
       "unit": "g/dL", "min_reference": "12.0", "max_reference": "16.0"}
    ]
  },
  "metadata": {
    "fixture_sha256": "computed-from-file",
    "scenario": "synthetic-mixed",
    "split": "development",
    "label_status": "requires-review",
    "rubric_version": "v1"
  }
}
```

This example illustrates a schema; it is not a finished one-row transcription
of the 15-row report. Task-specific schemas additionally cover expected errors,
severity labels, evidence packs, questions, and required/forbidden facts. Expected
labels never enter the application input. Keep development, calibration, and
held-out sets split by source document/template, not random rows of one report.

Review the goal, scenario mix, item schema, and first draft before uploading a
live dataset. Every AI-assisted transcription or proposed clinical label remains
unreviewed until a human confirms it.

## Integration architecture

```text
Versioned fixtures + reviewed expected outputs
                  |
           Experiment runner (Langfuse SDK)
                  |
      Real extraction / graph / MCP / chat paths
                  |
          Existing connected observations
                  |
     Shared deterministic evaluators + calibrated judges
                  |
      Scores on exact observations + experiment summary
                  |
      Compare models/prompts/rules -> reviewed promotion
```

Keep the existing `langfuse==5.0.1` SDK for the first implementation; use its
current experiment runner and score APIs, not removed legacy dataset-run APIs.

Add an evaluation module (`evals/`) containing item schemas, deterministic
comparators, experiment tasks, judge rubrics, frozen evidence adapters, and a
runner. Reuse those functions for offline experiments and live monitoring.
Mock model/retrieval dependencies only for wiring/unit tests; label experiments
that use real models and frozen retrieval distinctly from live retrieval canaries.

Before scoring, add explicit evaluation-ready observation inputs/outputs:

- Extraction: source text actually sent, raw model output, validated rows,
  retry outcome, cutoff flag and source fixture hash.
- Classification: source row, normalized identity/unit, selected range, critical
  bounds, range origin and rules version, result and stable row ID.
- Retrieval/explanation: query, exact evidence pack, source IDs and timestamps,
  generated explanation and next step, associated row ID.
- Chat: source panel/session, relevant history, question and final answer.

These are purposeful records rather than forcing evaluators to reverse-engineer
arbitrary LangGraph state. Preserve full synthetic content capture; add safe
evaluation metadata keys to the export allowlist instead of silently stripping
the data needed by evaluators. Record operation, prompt template hash/version,
commit, evaluator version, dataset version, requested/returned model and settings.
Prompt management is not yet implemented, so use content hashes until managed
prompt versions are available.

Attach extraction scores to the validated extraction operation, per-attempt
syntax scores to each attempt, per-row scores to the corresponding row/tool or
generation, chat scores to the answer generation, and whole-report pass/fail to
the request root. Trace and session scores are different aggregation levels.
Use a deterministic identity derived from observation + metric + evaluator
version so worker retries do not duplicate scores. Explicitly target one
operation/type: the root span and MCP tool can share a name in current traces.

The tracing helper currently starts a fresh request trace. For experiments,
deliberately link those roots to the experiment item or let the task adapter
inherit the experiment context. Verify that runner-created spans and application
roots do not become disconnected just because request isolation is enabled.

## Offline experiments first

1. Review the 10-family v0, transcriptions, policy labels, matching semantics,
   and metric definitions; publish the approved dataset version.
2. Baseline the current Qwen model and current prompts/rules. Include end-to-end
   PDF tests and isolated stages so upstream errors do not obscure attribution.
3. Compare candidate budget models with the same prompts, budgets, corpus,
   concurrency and evaluator versions. Vary one factor at a time.
4. Use frozen retrieval for reproducible comparisons; keep a separate live-search
   run to discover network/source drift. Store retrieved text used by each run.
5. Repeat stochastic cases (initial proposal: three repeats), report paired
   failures and counts, and estimate uncertainty when the dataset is large enough.
6. Keep task-model spending and evaluation-model spending separate, cap both,
   and compare cost per correct report as well as cost per attempted report.
7. Review failures before promoting a model/prompt. No automatic cheapest-model
   promotion based on a single average score.

## Calibrated judges, then asynchronous online evaluation

Start with deterministic evaluators and manual annotation. Review a representative
sample of full traces for unexpected failure modes; use that review to refine
the prose rubrics. For each judge, assemble approved pass/fail/borderline examples
with the same information it will see online. Tune on development examples and
measure a separate calibration/held-out slice.

Choose an independent, configurable judge model after comparison; do not use the
application's current model to certify itself by default. Benchmark judges for
false-pass and false-fail rates per failure category, stability across repeats,
and disagreement with domain reviewers. Overall agreement alone is insufficient.
Keep rules inactive until rubrics, mappings, and results are reviewed. Judge
model availability and pricing must be checked when selecting it.

Offline expected labels never become the judge's expected verdict input. Return
structured judgments with evidence, record evaluation errors as evaluation
errors, and treat missing evidence as not assessable rather than passing.

For live monitoring, use Langfuse asynchronous observation-level rules or a
separate evaluator worker; do not add judge calls to the analysis response path.
Initially apply cheap structural checks to all applicable runs and sample a
budgeted fraction for judges (proposal: 10%). Oversample failures/critical/unknown
cases for diagnosis but show those slices separately or weight them correctly;
their raw mean is not an unbiased traffic metric. The OpenRouter application
credential is not automatically a Langfuse managed-evaluator LLM connection.
Configure a server-side connection explicitly if using managed judges.

Online traces usually have no independently reviewed correct answer. Monitor
schema validity, factual consistency to available evidence, unsupported claims,
fallbacks, and behavior. Do not display online extraction accuracy or critical
recall unless the relevant source labels actually exist.

## Release gates and dashboard

Proposed initial gates on the reviewed P0 fixture set: zero changed source values,
zero invented/omitted required rows, zero missed expected critical cases, invariant
alias/unit cases, no session mixing, and explicit errors for unsupported inputs.
Require full deterministic-test success. These are fixture regression gates, not
claims of zero production error. If the baseline already fails a gate, report it
as a known failure to fix; do not redefine expected labels from the app output.

Track critical precision too: all-Critical output must not pass. Gate false alerts
against reviewed labels. Keep judge scores advisory until calibrated. Establish
repeated latency/cost baselines before proposing numerical performance thresholds;
10 scenario families do not support a meaningful production p95 estimate.

Run deterministic checks in every PR. Run paid benchmark experiments manually or
on approved trusted-branch changes initially, with budgets and credentials scoped
to trusted code. Introduce `langfuse/experiment-action` only after agreeing on
triggers, evaluators and regression thresholds. Keep held-out datasets separate
from routine prompt tuning.

Dashboard views should separate extraction, normalization/classification,
retrieval, explanation, chat, and operational outcomes; show sample counts,
versions and evaluator failures. Provide a list of actual failing cases and their
trace links. Avoid a single weighted score that lets fluent prose offset a
changed numeric value or missed critical case.

## Implementation order and acceptance

1. **Contracts and reviewed v0:** item schemas, row IDs/provenance, trace artifact
   audit, first draft review, approved labels and snapshot.
2. **Deterministic core:** extraction comparators, alias/unit tests, independent
   classification policy checks, online structural facts, trace-linked scores.
3. **Experiments:** baseline and paired candidate comparisons with replayable
   evidence and separate stage/end-to-end reports.
4. **Judges:** rubrics, expert labels, calibration experiments, disagreement
   review, then reviewed activation.
5. **Online and CI:** asynchronous sampled rules, dashboards, budgets, and agreed
   regression gates.

Verification must intentionally submit correct, altered-value, omitted-row,
unsupported-claim, judge-failure, duplicate-job and wrong-session examples.
Fetch the scores from Langfuse and confirm values, observation attachment,
evaluator version, idempotency, trace/experiment linkage and error status.
Unit tests or an evaluator appearing in the UI alone are insufficient.

## Sources

- [Choosing metrics](https://langfuse.com/academy/evaluate/choosing-what-to-evaluate)
- [Writing evaluators](https://langfuse.com/academy/evaluate/writing-evaluators)
- [Datasets](https://langfuse.com/docs/evaluation/experiments/datasets)
- [Experiments SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Scores API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)
- [LLM judges](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Judge calibration](https://langfuse.com/guides/llm-as-a-judge-calibration-skill)
- [CI experiments](https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd)
