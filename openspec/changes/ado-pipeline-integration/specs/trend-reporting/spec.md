## MODIFIED Requirements

### Requirement: Weekly report includes ADO progress section
The system SHALL include a Progress tab in weekly HTML reports that surfaces ADO work item status across all archived weeks.

#### Scenario: Progress tab injected into weekly report
- **WHEN** `generate_weekly_report()` is called and at least one archived week has rows with `ADOWorkItemId`
- **THEN** the weekly HTML report includes a Progress tab rendered via `build_report_html()` extra_nav/extra_sections injection

#### Scenario: ADO columns in master XLSX
- **WHEN** `update_master()` or `rebuild_master()` is called
- **THEN** `master_opportunities.xlsx` includes columns for `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOAssignedTo`, `ADOIteration`, `ADOLastUpdated`, and `ADOPushedAt` adjacent to the existing classification columns
