# Synthetic golden dataset draft v1

Historical draft only. Use [the active high-confidence v2](../v2/README.md).
These unreviewed v1 records must not be included in active evaluation runs.

This is a reviewable starting benchmark, not a clinically validated gold standard.
All 68 items have `label_status: requires_review`. No live Langfuse dataset was
created and no application output was used as ground truth.

## Contents

| File | Items | Expected results and intended checks |
| --- | ---: | --- |
| extraction.jsonl | 11 | Full row transcriptions, complete/incomplete/unsupported/invalid outcomes. JSON correctness, row recall/precision, exact field agreement. |
| classification.jsonl | 14 | Ten potassium boundary values, three glucose aliases, one report-range precedence case. Severity agreement and critical precision/recall. |
| normalization.jsonl | 6 | Scaling, equivalent units, valency mismatch, incompatible and absent units. Exact arithmetic and compatibility checks. |
| retrieval.jsonl | 5 | Relevant/irrelevant/empty/adversarial frozen evidence. Contextual relevancy and custom labeled ranking checks. |
| explanations.jsonl | 6 | Required/forbidden claims and rubric for numeric, normal, missing, qualified and injected contexts. Faithfulness, relevance and custom G-Eval. |
| workflow.jsonl | 8 | Normal/critical/qualitative routes, invalid rows, tool faults, missing lookup, concurrent rows. Tool correctness and custom trajectory assertions. |
| chat.jsonl | 6 | Multi-turn follow-up, absent facts, conflicting user assertion, diagnosis question, two-session isolation pair. Turn faithfulness and exact facts. |
| judge_calibration.jsonl | 12 | Six paired good/bad responses with proposed verdicts and reasons. Judge false-pass/false-fail checks. |

The source PDFs are in `output/pdf/golden-v1/` at the repository root. Start by
uploading `normal.pdf`, `critical-boundary.pdf`, `aliases.pdf`, or `units.pdf`.
The existing 15-row `Analyzer Service/test_data/dummy_lab_report.pdf` is included
by reference and has not been modified. Generated source text is in `fixtures/`.
`scanned.pdf` has an actual image and no text layer; OCR/VLM remains disabled.
`long.pdf` places a result after 12,000 extracted characters. Partial extraction
must not be scored as complete success. `fixtures/not-a-pdf.pdf` is intentionally
invalid and should only be used for failure testing.

## Item and execution contract

`item.schema.json` defines the shared envelope. Each record separates `input`,
`expected_output`, and `metadata`. Keep expected outputs out of application input.
Results are stored as strings to preserve decimal spelling, comma decimals and
qualifiers. Compare numeric meaning with decimal arithmetic where the application
normalizes numbers; compare `<5`, `3+`, and `Negative` without dropping qualifiers.
Use null for a genuinely missing field; a printed `-` remains an explicit source token.
Dates omitted from expected rows are not scored by this initial suite.

The future runner must adapt canonical rows to API schemas, resolve fixture paths
relative to the repo root, and expand evidence IDs from `evidence.json`. Source
page numbers can be derived from PDFs; this initial suite scores row contents and
does not claim page-attribution coverage. Do not send harness `faults` or
`tool_stubs` to the model: use them to configure mocked integration dependencies.
Tool calls use `{name, arguments}` in this neutral format; a DeepEval adapter must
map them to the installed SDK's ToolCall format. Required calls allow additional
legitimate calls; enforce forbidden calls separately. Order is local to each row,
not global across concurrently processed rows. Both session items must run
interleaved with distinct sessions to exercise isolation.

Behavior expectations are specifications, not claims that the current app passes.
For example, glucose aliases intentionally share the same expected status even
where the current alias lookup behaves inconsistently. Qualifier extraction can
pass even if downstream validation rejects unsupported numeric qualifiers; score
those stages independently. Missing/inverted ranges are preserved at extraction;
this is not an instruction to trust them during classification.

## Provenance and limitations

- PDF rows come from explicit authored source specifications. The mixed existing
  report transcription is a separately written draft checked against PDF text.
- `policy.json` freezes explicit draft classification bounds and inclusivity.
  These are software-policy regression labels, not universal clinical thresholds.
  Calcium mmol/L to mEq/L is labeled `mismatch` to match the intended interface
  requiring manual handling of valency; it is mathematically convertible by 2.
- `evidence.json` contains authored synthetic notes with reserved
  `example.invalid` URLs. They are not PubMed articles or medical citations.
  These fixtures test evidence handling, not real-world literature quality.
- Clinical and language-quality labels are AI-assisted proposals requiring human
  review. Calibration labels also need review before trusting judge agreement.
- Every report here is synthetic. Repeated rows and aliases are correlated cases,
  not independent patients. This small suite cannot estimate population accuracy.
- One injected document is reserved with `split: holdout` as a smoke fixture.
  It is visible in this repo and not a statistically meaningful blinded holdout.
  A later benchmark needs independent document templates and reviewed literature;
  reference-answer ContextualPrecision/Recall metrics are deferred until then.
- Initial coverage does not include live retrieval quality, every analyte,
  demographic-specific thresholds, multilingual PDF layouts, UI persistence, or
  every possible transport fault. Add these in later dataset versions.

## Review and reproduce

Review [REVIEW.md](REVIEW.md) alongside the JSONL records and fixtures. Confirm
exact transcriptions, policy thresholds, required/forbidden claims, and judge
verdicts. Record `reviewer`, `reviewed_at`, `review_notes`, and set `label_status`
to `approved` only after review; clinical-policy items need qualified review.

The generator overwrites generated artifacts, including review metadata. Preserve
approved versions separately before regenerating. Hashes in `manifest.json` freeze
this draft; intentional edits require an updated version/manifest before use.

From the repository root, using Python with reportlab, Pillow, pypdf and jsonschema:

```sh
python3 evals/generate_golden.py
python3 evals/validate_golden.py
```

Validation checks schemas, IDs, hashes, references, exact PDF row text, an actual
image-only scan, cutoff placement, decimal arithmetic, boundary-label consistency,
and balanced judge examples. It does not certify clinical truth or run an app
evaluation. No API keys or network access are needed.
