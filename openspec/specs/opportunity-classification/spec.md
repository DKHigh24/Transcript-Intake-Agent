## ADDED Requirements

### Requirement: Classify each candidate against the MVP schema
The system SHALL send each extracted candidate to the LLM with the classification system prompt and return a row conforming to `config/mvp_output_schema.json`.

#### Scenario: Candidate classified
- **WHEN** a candidate is submitted for classification
- **THEN** the system SHALL return a JSON object with all required MVP schema fields populated

#### Scenario: Classification failure on a candidate
- **WHEN** the LLM returns invalid JSON or an exception occurs
- **THEN** the system SHALL log a warning and skip that candidate, continuing with remaining candidates

### Requirement: Apply allowed choice values
The system SHALL validate enumerated fields (e.g., Priority, RequestingTeam, CurrentStatus) against `config/choice_values.json` and correct or flag invalid values.

#### Scenario: Valid choice value
- **WHEN** the LLM returns a value that matches an entry in `choice_values.json` for that field
- **THEN** the value SHALL be accepted as-is

#### Scenario: Invalid choice value
- **WHEN** the LLM returns a value not in the allowed list for that field
- **THEN** the system SHALL log a validation warning and substitute the nearest valid value or a safe default

### Requirement: Default status to Needs Review
All classified rows SHALL default `CurrentStatus` to `(2) Needs Review` unless explicitly overridden by configuration.

#### Scenario: Status defaulted
- **WHEN** a row is classified
- **THEN** `CurrentStatus` SHALL be `(2) Needs Review` unless `DEFAULT_STATUS` env var overrides it

### Requirement: All output is draft-only
The system SHALL treat all classified rows as draft output. No row SHALL be pushed to SharePoint without explicit human approval and pipeline configuration enabling the push.

#### Scenario: Push disabled by default
- **WHEN** `ENABLE_POWER_AUTOMATE_PUSH` is absent or `false`
- **THEN** the system SHALL write `output/sharepoint_payload.json` but SHALL NOT POST to the Power Automate endpoint

### Requirement: Persist classified rows to disk
The system SHALL write classified rows to `output/classified_rows.json` using the SharePoint internal field names from `config/sharepoint_field_mapping.json`.

#### Scenario: Rows persisted
- **WHEN** classification completes
- **THEN** `output/classified_rows.json` SHALL exist and each row SHALL use internal SharePoint field names as keys
