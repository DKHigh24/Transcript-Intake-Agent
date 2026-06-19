## MODIFIED Requirements

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
