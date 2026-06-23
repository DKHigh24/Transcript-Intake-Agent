## Why

Opportunities extracted from weekly transcripts are already pushed to ADO as Issues, but the pipeline has no awareness of what happens to them after push. Each week the team asks "where are we at with X?" — the answer requires manually checking ADO. This change wires ADO status sync into the weekly pipeline so reports automatically reflect live ADO state, and a new Progress tab surfaces movement on prior-week items without any manual lookup.

## What Changes

- `main.py` gains `--push-ado` flag: auto-pushes newly classified primary rows to ADO at end of weekly run (skips rows already with `ADOWorkItemId`)
- `main.py` runs `ado_client.sync_all_weeks()` automatically at the start of every `--mode weekly` run — no extra command needed
- `src/ado_client.py` (already built as POC) is promoted to a first-class pipeline module with `push_work_item()`, `sync_ado_status()`, `sync_all_weeks()`, and `get_or_create_epic()` as the public API
- `src/report_generator.py` gains ADO status chip on each opportunity card (state badge + link) and a new **Progress tab** showing movement on prior-week items grouped by ADO state
- `src/trend_reporter.py` gains an ADO Progress section in weekly HTML reports
- `config/mvp_output_schema.json` gains 7 new ADO tracking fields: `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, `ADOPushedAt`
- `master_opportunities.xlsx` gains corresponding ADO columns for Power BI

## Capabilities

### New Capabilities
- `ado-work-item-sync`: Weekly ADO status pull — queries all known work item IDs across all archived weeks, updates `classified_rows.json` with current state, iteration, assignee, and last-changed date before reports are rebuilt
- `ado-progress-reporting`: Progress tab in weekly HTML reports showing movement on all prior-week ADO items grouped by state (Moved This Week / Active / New / Resolved), and ADO status chips on individual opportunity cards

### Modified Capabilities
- `opportunity-classification`: Schema gains 7 new ADO tracking fields (`ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, `ADOPushedAt`) — all nullable, only populated post-push
- `trend-reporting`: Weekly reports gain ADO Progress section; opportunity cards gain ADO state chip and direct link

## Impact

- **Pipeline stages affected**: Steps 1 (no change), 2 (no change), 3 (schema fields), 4 (report output), 5 (no change); new pre-step 0 = ADO sync
- **New module**: `src/ado_client.py` (POC exists — needs promotion, error handling, sync_all_weeks)
- **New config**: `config/ado_field_mapping.json` — maps our schema fields to ADO REST API field paths
- **Schema change**: `config/mvp_output_schema.json` — 7 new nullable ADO fields
- **Master XLSX**: New ADO columns appended; `rebuild_master()` updated
- **Dependencies**: `requests` library (already installed for prior use); ADO PAT via `.env`
- **Secrets**: `ADO_PAT`, `ADO_ORG_URL`, `ADO_PROJECT` — all via `.env`, never committed
- **Backward compatible**: All ADO fields are nullable; pipeline runs normally without `.env` ADO vars (sync and push are silently skipped if PAT is absent)
