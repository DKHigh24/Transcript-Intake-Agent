## MODIFIED Requirements

### Requirement: Triage section in weekly HTML report
The weekly HTML report SHALL include a collapsible "Triage / Low Confidence" section below the main opportunity cards. This section SHALL display the count of suppressed candidates and list their titles and evidence summaries in a simplified card layout (no full card styling). If no candidates were suppressed, this section SHALL be omitted entirely.

#### Scenario: Suppressed candidates present
- **WHEN** one or more candidates were routed to Triage during the weekly run
- **THEN** the weekly HTML report includes a collapsed "Triage (N candidates)" section listing their titles and evidence

#### Scenario: No suppressed candidates
- **WHEN** all candidates met the confidence threshold
- **THEN** the Triage section is omitted from the weekly HTML report

### Requirement: Suppressed candidate transparency counter
The weekly HTML report summary header SHALL display a "candidates suppressed" count alongside the existing opportunity count, so reviewers understand the full extraction picture.

#### Scenario: Summary with suppressed count
- **WHEN** the weekly report is generated and N candidates were suppressed
- **THEN** the summary header reads "X opportunities identified, N suppressed (low confidence)" or similar
- **THEN** when N = 0 the suppressed count is omitted from the header
