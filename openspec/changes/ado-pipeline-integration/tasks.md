## 1. Config and Schema

- [x] 1.1 Add 7 ADO tracking fields to `config/mvp_output_schema.json`: `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, `ADOPushedAt` — all defaulting to `null`
- [x] 1.2 Create `config/ado_field_mapping.json` documenting the ADO REST API field paths used by `ado_client.py`
- [x] 1.3 Add `ADO_PARENT_EPIC_TITLE` default and PAT expiry renewal URL comment to `.env.example`

## 2. ado_client.py Promotion

- [x] 2.1 Add `sync_all_weeks()` function to `src/ado_client.py` — iterates all `output/weeks/*/classified_rows.json`, collects all `ADOWorkItemId` values, issues a single bulk GET per 200 IDs, writes back `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`
- [x] 2.2 Add graceful skip guard to all public functions — if `ADO_PAT` is empty, log `[ado] Skipping — ADO_PAT not configured` and return without raising
- [x] 2.3 Add HTTP error handling to `push_work_item()` and `sync_all_weeks()` — on non-200 response log warning with status code and continue (do not crash pipeline)
- [x] 2.4 Remove standalone `main()` CLI from `ado_client.py` (or keep as thin wrapper) — public API is now `push_work_item()`, `sync_all_weeks()`, `get_or_create_epic()`

## 3. main.py Pipeline Wiring

- [x] 3.1 Add `--push-ado` flag to `main.py` argparser (boolean, default False)
- [x] 3.2 Add Step 0 in `run_weekly()`: call `ado_client.sync_all_weeks()` before extract/classify — wrapped in try/except so ADO failure never blocks the pipeline
- [x] 3.3 Add Step post-archive in `run_weekly()`: if `--push-ado` is True, call `ado_client.get_or_create_epic()` then push all primary rows without `ADOWorkItemId`
- [x] 3.4 Pass `--push-ado` value through `run_weekly()` signature

## 4. report_generator.py — ADO Card Chip

- [x] 4.1 Add ADO state chip rendering to `_build_cards_html()` — show state badge + `🔗` link when `ADOWorkItemId` is present; render nothing when null
- [x] 4.2 Add `data-ado-status` attribute to card `div` for potential future JS filtering
- [x] 4.3 Define ADO state colors in a `ADO_STATE_COLORS` dict: New=gray, Active=blue, Resolved=green, Closed=dark gray

## 5. report_generator.py — Progress Tab

- [x] 5.1 Add `_build_progress_tab(all_historical_rows)` function that accepts a flat list of rows from all weeks, groups by `ADOStatus`, identifies "Moved This Week" (ADOLastUpdated within 7 days), and returns HTML string
- [x] 5.2 Build the Progress tab HTML: sections for Moved This Week / Active / New / Resolved / Closed; each item shows title, week raised, ADO ID + link, assignee, iteration
- [x] 5.3 Expose `build_progress_tab_injection(all_rows)` returning `(extra_nav, extra_section)` tuple for injection into `build_report_html()`

## 6. trend_reporter.py — Progress Tab Injection

- [x] 6.1 In `generate_weekly_report()`, load all historical `classified_rows.json` files (already done for trend data) and collect rows with `ADOWorkItemId` across all weeks
- [x] 6.2 Call `report_generator.build_progress_tab_injection(ado_rows)` and pass result into `build_report_html()` via `extra_nav` / `extra_sections`

## 7. master_exporter.py — ADO Columns

- [x] 7.1 Add ADO tracking columns to `master_opportunities.xlsx` output: `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOAssignedTo`, `ADOIteration`, `ADOLastUpdated`, `ADOPushedAt` — appended after existing classification columns
- [x] 7.2 Ensure `rebuild_master()` picks up ADO fields from archived `classified_rows.json`

## 8. Verification

- [x] 8.1 Run `main.py --mode weekly` on the 6/17 transcript (no `--push-ado`) — confirm sync runs, 9 existing items have their ADO status updated, no new pushes occur
- [x] 8.2 Open the rebuilt `weekly_report.html` — confirm ADO chips appear on all 9 cards from 6/17, Progress tab shows all items grouped by state
- [x] 8.3 Run `main.py --mode weekly --push-ado` on a test row (or confirm skip for already-pushed rows) — title dedup recovers existing items, no duplicates created
- [x] 8.4 Open `master_opportunities.xlsx` — confirm ADO columns are present (Excel file lock handled gracefully with warning)
