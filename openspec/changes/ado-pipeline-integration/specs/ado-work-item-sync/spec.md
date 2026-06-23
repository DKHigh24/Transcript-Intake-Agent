## ADDED Requirements

### Requirement: Weekly ADO status sync runs automatically
The system SHALL query ADO for current state of all known work items at the start of every `--mode weekly` pipeline run, before any reports are generated.

#### Scenario: PAT present and items exist
- **WHEN** `main.py --mode weekly` is run and `ADO_PAT` is set in `.env` and any archived `classified_rows.json` file contains rows with `ADOWorkItemId`
- **THEN** the system queries ADO for all known IDs in bulk, updates `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, and `ADOLastUpdated` in each week's `classified_rows.json` before rebuilding reports

#### Scenario: PAT absent — graceful skip
- **WHEN** `main.py --mode weekly` is run and `ADO_PAT` is not set in `.env`
- **THEN** the ADO sync step is silently skipped, a single log line `[ado] Skipping sync — ADO_PAT not configured` is printed, and the pipeline continues normally

#### Scenario: ADO API error
- **WHEN** the ADO API returns a non-200 response during sync
- **THEN** the system logs a warning with the HTTP status code and continues without updating rows (last-known state is preserved)

### Requirement: Push new opportunities to ADO via opt-in flag
The system SHALL push newly classified primary rows as ADO work items when `--push-ado` is passed to `main.py --mode weekly`.

#### Scenario: New rows pushed
- **WHEN** `main.py --mode weekly --push-ado` is run and classified rows exist without `ADOWorkItemId`
- **THEN** each row without `ADOWorkItemId` is pushed as an Issue under the configured parent Epic, and `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, and `ADOPushedAt` are written back to `classified_rows.json`

#### Scenario: Already-pushed rows skipped
- **WHEN** a row already has `ADOWorkItemId` set
- **THEN** the push is skipped for that row — no duplicate work item is created

#### Scenario: Push without flag — no push
- **WHEN** `main.py --mode weekly` is run without `--push-ado`
- **THEN** no ADO push occurs regardless of whether new rows exist

### Requirement: ADO tracking fields stored per row
The system SHALL maintain 7 ADO tracking fields on each classified row: `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, `ADOPushedAt`.

#### Scenario: Fields default to null
- **WHEN** a row is classified but not yet pushed to ADO
- **THEN** all 7 ADO fields are `null` in `classified_rows.json`

#### Scenario: Fields populated after push
- **WHEN** a row is successfully pushed to ADO
- **THEN** `ADOWorkItemId` (integer), `ADOUrl` (string), `ADOStatus` (string), and `ADOPushedAt` (ISO-8601 UTC) are written back immediately

#### Scenario: Fields updated after sync
- **WHEN** ADO sync runs and the work item has changed state
- **THEN** `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, and `ADOLastUpdated` are updated in `classified_rows.json`

### Requirement: Sync covers all archived weeks
The system SHALL sync ADO status across ALL week directories, not just the current week.

#### Scenario: Multi-week sync
- **WHEN** ADO sync runs
- **THEN** all `output/weeks/*/classified_rows.json` files are checked for rows with `ADOWorkItemId` and updated in a single bulk API call per 200 IDs
