## ADDED Requirements

### Requirement: ADO status chip on opportunity cards
The system SHALL display an ADO state chip and link on each opportunity card that has been pushed to ADO.

#### Scenario: Card with ADO item
- **WHEN** an opportunity card is rendered and the row has a non-null `ADOWorkItemId`
- **THEN** the card displays an ADO state badge (e.g. `🔵 Active`, `✅ Resolved`, `⬜ New`) and a clickable link that opens the ADO work item in a new browser tab

#### Scenario: Card without ADO item
- **WHEN** an opportunity card is rendered and `ADOWorkItemId` is null
- **THEN** no ADO chip or link is shown; the card renders identically to before this change

#### Scenario: ADO chip color coding
- **WHEN** the ADO state chip is rendered
- **THEN** state colors are: New = gray, Active = blue (#2563EB), Resolved = green (#059669), Closed = dark gray (#374151)

### Requirement: Progress tab on weekly HTML reports
The system SHALL include a Progress tab on weekly HTML reports showing movement on all ADO-linked items across all prior weeks.

#### Scenario: Items moved this week
- **WHEN** the Progress tab is rendered and any ADO-linked rows have `ADOLastUpdated` within the last 7 days
- **THEN** those items appear in a "Moved This Week" section showing old→new state, assignee, and iteration

#### Scenario: Items grouped by ADO state
- **WHEN** the Progress tab is rendered
- **THEN** all ADO-linked items across all weeks are grouped into sections: Active, New (no action), Resolved, Closed

#### Scenario: No ADO items pushed yet
- **WHEN** the Progress tab is rendered and no rows across any week have `ADOWorkItemId`
- **THEN** the Progress tab shows a placeholder message "No items have been pushed to ADO yet"

#### Scenario: Item history thread
- **WHEN** an item is shown in the Progress tab
- **THEN** it displays: week raised, date pushed to ADO, current ADO state, assignee, and iteration path
