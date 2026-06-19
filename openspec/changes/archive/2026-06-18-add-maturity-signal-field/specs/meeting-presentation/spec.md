## MODIFIED Requirements

### Requirement: PPTX deck includes Live Wins section
`src/presentation_builder.py` SHALL add a "Live Wins This Week" slide section when any
rows in `last_week_rows` have `MaturitySignal == "Delivered / Active Today"`.

The section SHALL appear before the full opportunity list slide, highlighting delivered
items as concrete achievements rather than proposals.

If no delivered rows are present for the week, the section SHALL be omitted entirely
(no empty "Live Wins" slide).

#### Scenario: Live wins slide generated when delivered rows exist
- **WHEN** the weekly classified rows contain one or more `Delivered / Active Today` rows
- **THEN** the PPTX SHALL include a "Live Wins This Week" slide listing those opportunities
  with their Title, ProcessStage, SubOrdinateFunction, and EvidenceSummary

#### Scenario: Live wins slide omitted when no delivered rows
- **WHEN** no classified rows for the week have `MaturitySignal == "Delivered / Active Today"`
- **THEN** the PPTX SHALL NOT include a "Live Wins This Week" slide

#### Scenario: All maturity signals present in slide notes
- **WHEN** any opportunity slide is generated
- **THEN** the speaker notes for that slide SHALL include the `MaturitySignal` value so
  presenters can speak to the status during the meeting
