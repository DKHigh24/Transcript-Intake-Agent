## MODIFIED Requirements

### Requirement: Classifier produces complete MVP schema row
The classifier SHALL produce a JSON object for each candidate that includes all fields
from `config/mvp_output_schema.json`, now including `MaturitySignal`.

The classifier skill (skills/classify_opportunities.md) SHALL instruct the LLM to:
- Infer `MaturitySignal` from the verbatim evidence using the linguistic marker vocabulary
  defined in the maturity-signal-detection spec
- Default to `"Unknown"` when evidence is ambiguous
- Never leave `MaturitySignal` blank — always select one of the four allowed values

#### Scenario: Classified row includes MaturitySignal
- **WHEN** the classifier processes a candidate opportunity
- **THEN** the output JSON SHALL contain `"MaturitySignal"` with a value from
  `config/choice_values.json["MaturitySignal"]`

#### Scenario: Validation passes for all four MaturitySignal values
- **WHEN** validators.py validates classified rows
- **THEN** any row with `MaturitySignal` in `["Aspirational", "In Progress / Piloting",
  "Delivered / Active Today", "Unknown"]` SHALL pass validation without warning

### Requirement: Confidence floor routing
After classification, the pipeline SHALL apply a confidence floor filter. Rows classified with `ConfidenceLevel = "Low"` SHALL be routed to the Triage sheet of `review_rows.xlsx` and excluded from `master_opportunities.xlsx` and HTML report cards by default.

A `--include-low-confidence` CLI flag SHALL override this behavior and include low-confidence rows on all primary surfaces (main sheet, master XLSX, and HTML cards) identical to how high-confidence rows are presented.

#### Scenario: Low-confidence row excluded by default
- **WHEN** a classified row has ConfidenceLevel = "Low" and `--include-low-confidence` is not set
- **THEN** the row appears only on the Triage sheet of review_rows.xlsx and is excluded from master_opportunities.xlsx and HTML report cards

#### Scenario: Low-confidence row included via flag
- **WHEN** a classified row has ConfidenceLevel = "Low" and `--include-low-confidence` IS set
- **THEN** the row is treated identically to Medium/High confidence rows across all outputs

#### Scenario: Medium and High confidence rows unaffected
- **WHEN** a classified row has ConfidenceLevel = "Medium" or "High"
- **THEN** it always appears on the main review sheet, master XLSX, and HTML report cards regardless of any flags
