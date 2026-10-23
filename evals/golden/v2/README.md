# High-confidence golden datasets v2

All **eight datasets are populated and verified**, with **67 cases**. Human
review is not a prerequisite for this deliberately restricted software benchmark.
Labels are `machine_verified`, not `human_approved` or `clinically_validated`.

| Dataset | Cases | High-confidence basis | Completion |
| --- | ---: | --- | --- |
| extraction | 11 | Exact PDF row text and bounds; malformed format; image-only scan; tail beyond text cutoff | Complete |
| classification | 12 | Fictional assay and explicit mathematical bounds, boundary inclusivity, absent range | Complete |
| normalization | 7 | SI arithmetic, unit equivalence, incompatible dimensions, explicit analyte alias contract | Complete |
| retrieval | 5 | Topic membership in a closed synthetic evidence set; empty, irrelevant and injected material | Complete |
| explanations | 6 | Original value/unit/qualifier, decimal comparison to the printed interval, evidence allowlist | Complete |
| workflow | 8 | Stubbed classifier returns and graph contracts; calls/arguments, branches, partial failures, concurrency | Complete |
| chat | 6 | Source report facts, missing measurements, contradictory assertions, units, two-session isolation | Complete |
| judge_calibration | 12 | Six paired correct/incorrect answers with explicit factual witnesses | Complete |

## What changed from v1

- Removed patient-specific critical threshold expectations. Classification now
  uses `Synthetic Assay A`, normal interval 10–20 and critical bounds 5–25,
  with strict critical and inclusive normal comparisons. These values test
  arithmetic and software behavior; they have no medical meaning.
- Replaced advice/diagnosis expectations with exact report-fact expectations.
  No clinician-authored treatment, urgency, causal or diagnostic labels are used.
- Replaced medical evidence notes with literal synthetic report excerpts.
  Retrieval labels follow explicit topic membership, not literature judgment.
- Removed the calcium conversion row that conflated a physically convertible
  quantity with the application's unsupported conversion behavior. Removed the
  missing-unit row that could suggest a verified conversion despite absent units.
- Added explicit alias-contract cases without attaching medical severity labels.
- Replaced the diagnosis chat case with a unit lookup. Replaced the medical
  causal calibration pair with a numerical source-consistency pair.
- Workflow classifier returns are controlled stubs. A Critical stub tests the
  critical branch; it does not establish that any patient's result is critical.
- Removed the misleading visible-document holdout designation. These are
  development and calibration fixtures, not a blinded statistical benchmark.

## Verification and use

Run `evals/curate_golden.py` to build and verify; run `evals/verify_golden.py` to
check the frozen files again. Both work with the existing backend Python venv.
The curator initially writes pending labels. It promotes them to
`machine_verified` only after independent source/arithmetic/contract checks pass.
Any failed verification exits unsuccessfully; pending rows are not usable golden
labels. The final manifest freezes JSONL data, source PDFs, schema, policy,
evidence, and verification scripts with SHA-256 hashes.

`evals/test_golden_integrity.py` additionally checks that a false expected label
in each of the eight categories and an empty dataset are rejected (16 negative
subcases). Run it with the same backend Python environment.

`input`, `expected_output`, and `metadata` stay separate. Never send expected
outputs to the application. `alias_contract` and workflow `tool_stubs`/`faults`
configure the evaluation harness, not the model prompt. Fault injection takes
precedence over a configured successful stub. The keyed classifier stub in the
parallel case responds by test name. Enforce order within a row, not across rows.

For explanations/chat, `required_facts` are structured factual obligations, not
exact prose to match. A comparator must allow numeric formatting and wording
variations while preserving meaning. Missing tests must not gain invented values.
The two session cases must run interleaved in distinct sessions. Checking dataset
labels does not prove that an LLM evaluator or the application handles them.

The reference PDFs remain in `output/pdf/golden-v1/` and the existing app test-data
folder. Source strings preserve qualifiers and comma decimals. Dates and page
attribution are not scored by this version. The long-report case targets the
current 12,000-character budget; change its contract if that limit is removed.

## Limits of completion

All eight requested dataset categories are complete **within this scope**. This
does not mean all application behaviors or medical use cases are covered.
Clinical diagnosis, treatment appropriateness, true patient urgency, demographic
thresholds and medical-source quality are deliberately excluded. Live literature
retrieval, production distributions, multilingual/scanned OCR, UI persistence
and a full upload-to-reload browser scenario are not claimed covered here.

The judge anchors test obvious factual errors. They do not certify judge quality
on ambiguous prose. Calibration accuracy can only be reported after running a
judge; these labels must not be described as empirical judge-performance results.
Likewise, deterministic labels do not make DeepEval's language judges deterministic.

The verification command checks dataset integrity and its proof obligations,
not application pass rates. No DeepEval runner, live Langfuse upload or production
scoring was executed as part of this dataset update.
