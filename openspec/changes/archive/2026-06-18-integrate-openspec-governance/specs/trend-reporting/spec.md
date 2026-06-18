## ADDED Requirements

### Requirement: Ingest classified rows into opportunity history
The system SHALL merge each week's classified rows into `output/history/opportunities.json`, deduplicating by opportunity title across all sessions.

#### Scenario: New opportunity added
- **WHEN** a classified row has a title not present in history
- **THEN** it SHALL be appended to the history with its session date

#### Scenario: Existing opportunity updated
- **WHEN** a classified row title matches an existing history entry
- **THEN** the history entry SHALL be updated with the latest classification data

### Requirement: Generate weekly HTML trend report
The system SHALL generate an HTML report for each week showing the opportunities identified that week, counts by category, and comparison to the prior week.

#### Scenario: Weekly report generated
- **WHEN** a week's classified rows are available
- **THEN** the system SHALL write `output/weeks/<YYYY-MM-DD>/weekly_report.html` with opportunity count, team breakdown, and priority distribution

### Requirement: Generate monthly HTML trend report
The system SHALL generate a monthly HTML report aggregating all unique opportunities identified within that calendar month.

#### Scenario: Monthly report generated
- **WHEN** history contains entries for a given month
- **THEN** the system SHALL write `output/reports/monthly_<YYYY-MM>.html` with unique opportunity count and longitudinal trend data

### Requirement: Rebuild all reports on back-dated transcript
The system SHALL detect when a transcript's date is not strictly newer than the existing history maximum, and SHALL rebuild all weekly and monthly reports to maintain longitudinal accuracy.

#### Scenario: Back-dated transcript detected
- **WHEN** the processed transcript date is less than or equal to the current history maximum date
- **THEN** the system SHALL regenerate all existing weekly and monthly reports after ingesting the new data

### Requirement: Archive weekly artifacts
The system SHALL copy `classified_rows.json`, `review_rows.xlsx`, and `sharepoint_payload.json` to `output/weeks/<YYYY-MM-DD>/` at the end of each weekly run.

#### Scenario: Artifacts archived
- **WHEN** a weekly run completes
- **THEN** the three artifact files SHALL exist in the week's archive directory
