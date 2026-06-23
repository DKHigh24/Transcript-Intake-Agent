## Context

The pipeline already successfully extracts, classifies, and pushes opportunity cards as ADO Issues (POC complete — Issues #40–48 live in `CXAEO/Opportunities`). The `ado_client.py` module exists but is a standalone CLI tool. It is not integrated into the weekly pipeline run, and the HTML reports have no awareness of ADO state. Each week the team manually checks ADO to answer "where are we at" questions about items raised in prior sessions.

**Current weekly run:** `main.py --mode weekly` → extract → classify → export XLSX → build HTML reports → build PPTX. No ADO awareness.

**Target weekly run:** Same flow with ADO sync prepended (auto) and ADO push appended (opt-in via `--push-ado`). Reports surface live ADO state on every card and a Progress tab answers "where are we at" without manual ADO lookup.

## Goals / Non-Goals

**Goals:**
- Auto-sync ADO status at the start of every `--mode weekly` run (silently skipped if `ADO_PAT` absent)
- Wire `--push-ado` flag into `main.py` so new primary rows are pushed without a separate command
- Surface ADO state chip + link on every opportunity card that has been pushed
- Add a Progress tab to weekly HTML reports showing movement on all prior ADO items
- Add ADO columns to `master_opportunities.xlsx` for Power BI
- Keep ADO integration fully optional — pipeline runs identically without ADO credentials

**Non-Goals:**
- Two-way field sync (we do not write ADO field changes back to classified_rows beyond status/assignee)
- ADO comment ingestion
- Creating ADO Sprints/Iterations programmatically
- Monthly report ADO section (deferred — weekly first)
- PPTX ADO slides (deferred)

## Decisions

### Decision 1: Sync runs automatically; push requires explicit opt-in
**Chosen:** Sync = automatic at weekly start; Push = `--push-ado` flag only.  
**Rationale:** Sync is read-only and safe to run always — it only updates local JSON. Push creates ADO items and should be a deliberate human action. Forcing `--push-ado` prevents accidental duplicate items during re-runs or back-dated ingests.  
**Alternative considered:** Auto-push as part of every weekly run → rejected because re-running a transcript (e.g. for re-extraction) would duplicate ADO items.

### Decision 2: ADO sync as a pre-step before report generation (not post-step)
**Chosen:** Sync happens at Step 0, before extract/classify. Reports are always generated with the freshest ADO state.  
**Rationale:** The primary value is in reports reflecting current ADO state. If sync ran post-reports, reports would be stale until next run.  
**Alternative:** Run sync after classify, before report generation → also valid, chosen pre-step to keep pipeline stages clean.

### Decision 3: `ado_client.py` promoted to pipeline module (not subprocess)
**Chosen:** `main.py` imports `ado_client` directly; sync and push are function calls.  
**Rationale:** Subprocess calls add latency and make error handling awkward. Direct import keeps the module boundary clean and allows `main.py` to gracefully skip ADO if credentials are absent.  
**Guard:** All ADO functions check for `ADO_PAT` at call time and return early (not raise) when missing — ensuring backward compatibility.

### Decision 4: ADO fields stored in `classified_rows.json` alongside classification fields
**Chosen:** Append ADO fields to each row dict in `classified_rows.json` in-place.  
**Rationale:** Single source of truth per week. `master_exporter.py` and `report_generator.py` already read from this file — ADO fields come along for free. No separate ADO state file to keep in sync.

### Decision 5: Progress tab built from cross-week ADO field aggregation
**Chosen:** `report_generator.build_report_html()` receives all historical rows (with ADO fields) from `trend_reporter.py`; Progress tab groups by `ADOStatus` and highlights items with `ADOLastUpdated` within the last 7 days as "Moved This Week".  
**Alternative:** Separate `ado_progress_reporter.py` module → rejected as over-engineering for the current scale.

## Risks / Trade-offs

- **PAT expiry** → Sync silently fails with a logged warning; reports show last-known ADO state. Mitigation: `.env.example` documents PAT expiry; warning message includes renewal URL.
- **ADO rate limiting** → Bulk `workitems?ids=` endpoint handles up to 200 IDs per call; current volume (< 50 items) is well within limits. Mitigation: batch calls if count exceeds 200.
- **Duplicate push guard** → Rows with existing `ADOWorkItemId` are skipped. Re-running `--push-ado` on a week that was already pushed is safe. Mitigation: guard already implemented in POC.
- **ADO field name drift** → If the project changes work item type or area path, pushed items may fail. Mitigation: all ADO config in `.env`; `ado_field_mapping.json` documents field paths.
- **Classified_rows.json mutation** → Sync writes back to the archived JSON files. Mitigation: files are output artifacts (gitignored); write is idempotent (overwrites same fields).

## Migration Plan

1. No migration needed for existing weeks — ADO fields default to `null` in schema; existing reports unaffected
2. For the 9 already-pushed items (Issues #40–48 from 6/17): `--sync` will populate their `ADOStatus`, `ADOAssignedTo`, etc. on next weekly run automatically
3. For prior weeks (5/7–6/10): rows have no `ADOWorkItemId`; cards render without ADO chip (graceful degradation)
4. Rollback: remove `--push-ado` flag from run command; ADO sync is read-only and safe to leave enabled

## Open Questions

- None blocking implementation. ADO project (`CXAEO/Opportunities`), work item type (`Issue`), and Epic (`#39`) are confirmed working from POC.
