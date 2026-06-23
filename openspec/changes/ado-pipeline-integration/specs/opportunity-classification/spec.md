## MODIFIED Requirements

### Requirement: Classification output conforms to MVP schema
The system SHALL produce classified rows that include all fields defined in `config/mvp_output_schema.json`, including the 7 new ADO tracking fields.

#### Scenario: Schema includes ADO tracking fields
- **WHEN** a row is classified
- **THEN** the output includes `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, and `ADOPushedAt`, all defaulting to `null`

#### Scenario: ADO fields not overwritten by classifier
- **WHEN** a row already has ADO fields populated (from a prior push/sync)
- **THEN** the classifier does not overwrite those fields during re-classification
