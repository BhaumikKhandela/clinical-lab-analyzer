# Golden dataset review queue

All expected results are unreviewed proposals.
Review the source fixture and expected output before changing label_status.
Record reviewer, date, rationale, and policy/source version in metadata.
Clinical-policy labels need clinical review; generator reruns overwrite generated files.

| Dataset | Item | Family | Clinical review |
| --- | --- | --- | --- |
| extraction | extract-mixed | mixed-panel | False |
| extraction | extract-normal | normal | False |
| extraction | extract-critical-boundary | critical-boundary | False |
| extraction | extract-aliases | aliases | False |
| extraction | extract-units | units | False |
| extraction | extract-qualifiers | qualifiers | False |
| extraction | extract-ranges | ranges | False |
| extraction | extract-long | long | False |
| extraction | extract-scanned | scanned | False |
| extraction | extract-injection | injection | False |
| extraction | extract-invalid | invalid | False |
| classification | potassium-2.49 | critical-boundary | True |
| classification | potassium-2.50 | critical-boundary | True |
| classification | potassium-2.51 | critical-boundary | True |
| classification | potassium-3.49 | critical-boundary | True |
| classification | potassium-3.50 | critical-boundary | True |
| classification | potassium-5.10 | critical-boundary | True |
| classification | potassium-5.11 | critical-boundary | True |
| classification | potassium-6.49 | critical-boundary | True |
| classification | potassium-6.50 | critical-boundary | True |
| classification | potassium-6.51 | critical-boundary | True |
| classification | glucose-alias-0 | aliases | True |
| classification | glucose-alias-1 | aliases | True |
| classification | glucose-alias-2 | aliases | True |
| classification | range-precedence | ranges | True |
| normalization | hemoglobin-scale | units | False |
| normalization | count-equivalence | units | False |
| normalization | potassium-valency | units | False |
| normalization | calcium-valency | units | False |
| normalization | incomparable | units | False |
| normalization | missing-unit | units | False |
| retrieval | potassium-mixed | evidence | True |
| retrieval | glucose-mixed | evidence | True |
| retrieval | empty | evidence | True |
| retrieval | irrelevant | evidence | True |
| retrieval | injection | evidence | True |
| explanations | low-potassium | explanations | True |
| explanations | glucose | explanations | True |
| explanations | normal | explanations | True |
| explanations | no-evidence | explanations | True |
| explanations | qualifier | explanations | True |
| explanations | injected-evidence | explanations | True |
| workflow | normal-path | workflow | False |
| workflow | critical-path | workflow | True |
| workflow | qualitative-path | workflow | False |
| workflow | mixed-validity | workflow | False |
| workflow | search-failure | workflow | False |
| workflow | classifier-failure | workflow | False |
| workflow | lookup-missing | workflow | False |
| workflow | parallel-rows | workflow | False |
| chat | followup | chat | False |
| chat | missing | chat | False |
| chat | contradiction | chat | False |
| chat | diagnosis | chat | True |
| chat | session-a | chat | False |
| chat | session-b | chat | False |
| judge_calibration | judge-numeric-pass | judge-calibration | False |
| judge_calibration | judge-numeric-fail | judge-calibration | False |
| judge_calibration | judge-range-pass | judge-calibration | False |
| judge_calibration | judge-range-fail | judge-calibration | False |
| judge_calibration | judge-missing-pass | judge-calibration | False |
| judge_calibration | judge-missing-fail | judge-calibration | False |
| judge_calibration | judge-qualifier-pass | judge-calibration | False |
| judge_calibration | judge-qualifier-fail | judge-calibration | False |
| judge_calibration | judge-evidence-pass | judge-calibration | True |
| judge_calibration | judge-evidence-fail | judge-calibration | True |
| judge_calibration | judge-relevance-pass | judge-calibration | False |
| judge_calibration | judge-relevance-fail | judge-calibration | False |
