## ADDED Requirements

### Requirement: MaturitySignal field in config
The system SHALL add `MaturitySignal` as a controlled-vocabulary choice field in
`config/choice_values.json` with exactly four values: `Aspirational`,
`In Progress / Piloting`, `Delivered / Active Today`, `Unknown`.

The system SHALL add `MaturitySignal: ""` to `config/mvp_output_schema.json` positioned
after `ConfidenceLevel`.

The system SHALL add `"MaturitySignal": "MaturitySignal"` to
`config/sharepoint_field_mapping.json`.

#### Scenario: New run produces MaturitySignal
- **WHEN** a transcript is processed through the full pipeline
- **THEN** every classified row SHALL contain a `MaturitySignal` field with one of the
  four allowed values

#### Scenario: Unknown default for ambiguous evidence
- **WHEN** the classifier cannot determine maturity from the evidence
- **THEN** `MaturitySignal` SHALL be set to `"Unknown"` rather than left blank

### Requirement: Linguistic marker detection in classifier
The classifier skill SHALL instruct the LLM to infer `MaturitySignal` from verbatim
evidence phrases using the following signal vocabulary:

- **Aspirational**: "we should", "what if", "I'd love to see", "has anyone tried",
  "we need to build", "could we", "imagine if"
- **In Progress / Piloting**: "we're currently", "we started", "proof of concept",
  "in evaluation", "we're testing", "we have a pilot", "we're exploring"
- **Delivered / Active Today**: "we're already using", "this is live", "we deployed",
  "it's running", "we built this", "this is working today", "we have this today"

#### Scenario: Aspirational signal detected
- **WHEN** the evidence contains future-tense or proposal-language phrases
- **THEN** `MaturitySignal` SHALL be `"Aspirational"`

#### Scenario: Active delivery signal detected
- **WHEN** the evidence contains present-tense delivery confirmation phrases
- **THEN** `MaturitySignal` SHALL be `"Delivered / Active Today"`

#### Scenario: In-progress signal detected
- **WHEN** the evidence contains piloting or evaluation language
- **THEN** `MaturitySignal` SHALL be `"In Progress / Piloting"`
