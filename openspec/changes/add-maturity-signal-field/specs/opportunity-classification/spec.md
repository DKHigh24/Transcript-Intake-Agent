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
