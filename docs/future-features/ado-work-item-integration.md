# ADO Work Item Integration

**Status**: ✅ Implemented — shipped in commit `b93b1f3` (2026-06-23)
**Designed**: 2026-06-18 (proposed)
**Implemented**: 2026-06-23 (via OpenSpec change `ado-pipeline-integration`)

---

## What Was Built

The ADO integration was added as a feature to **close the loop on where the work actually occurs**. AI opportunities identified from meeting transcripts are only valuable if someone picks them up and makes progress. Without a connection to a work tracking system, the group has no way to answer *"we talked about invoice matching automation three weeks ago — has anything happened?"*

Three sub-capabilities were implemented together:

---

### 1. `--push-ado` — Push opportunities to ADO as Issues

**Module:** `src/ado_client.py` → `push_work_item(row, epic_id)`  
**Trigger:** `--push-ado` flag on `main.py --mode weekly` (opt-in; never automatic)

Each primary row that does not already have an `ADOWorkItemId` is created as an **Issue** in ADO under the configured parent Epic. The rich HTML description includes:

- Problem / pain point
- Evidence quote from the transcript with speaker, timestamp, and meeting date
- Recommended next step
- Classification metadata table (MaturitySignal, OperatingBucket, ProcessStage, SubFunction, Confidence)
- Draft provenance disclaimer

Tags are automatically generated from `MaturitySignal`, `OperatingBucket`, `AIUseCaseType`, and `ProcessStage`.

**Dedup guard:** Before creating a new item, the client queries ADO by title using WIQL. If an item with that exact title already exists, it recovers the existing ID instead of creating a duplicate. This makes `--push-ado` safe to re-run after a partial failure or pipeline re-run.

**Write-back:** After push, `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, and `ADOPushedAt` are written back to the archived `classified_rows.json`. This ensures the Step 0 sync can track the item from that point forward.

---

### 2. Automatic ADO status sync (Step 0)

**Module:** `src/ado_client.py` → `sync_all_weeks()`  
**Trigger:** Runs automatically at the start of every `--mode weekly` pipeline run

All archived `classified_rows.json` files are scanned for `ADOWorkItemId` values. These are deduplicated, batched in groups of 200 (ADO bulk GET limit), and queried in a single round-trip per batch. The response updates:

- `ADOStatus` — current state (`To Do` / `Doing` / `Done` for Basic process)
- `ADOIteration` — current sprint or iteration path
- `ADOAssignedTo` — display name of the assigned team member
- `ADOLastUpdated` — ISO timestamp of the last state change

This sync is **read-only** — it never creates or modifies ADO items. It is skipped silently if `ADO_PAT` is not set in `.env`. Failures do not block the pipeline.

---

### 3. Progress tab — "Where are we at?"

**Module:** `src/report_generator.py` → `_build_progress_tab()`, `build_progress_tab_injection()`  
**Module:** `src/trend_reporter.py` → `generate_weekly_report()` (injected as fifth tab)

Every weekly HTML report now has a **🔄 Progress** tab. It:

- Collects all ADO-linked rows across **all** archived weeks
- Groups them by current ADO state: **Doing**, **To Do**, **Done**
- Identifies items whose `ADOLastUpdated` falls within the past 7 days as **"Moved This Week"** — highlighted at the top
- For each item shows: ADO # (linked), title, assignee, iteration, last-updated date, and the week it was originally raised

This directly answers the *"where are we at with X we discussed in May?"* question without manual lookups in ADO.

---

## Configuration

```env
ADO_ORG_URL=https://dev.azure.com/YourOrg
ADO_PROJECT=YourProject
ADO_PAT=your-personal-access-token
# Renewal: https://dev.azure.com/YourOrg/_usersSettings/tokens
# Required scopes: Work Items (Read & Write)

ADO_WORK_ITEM_TYPE=Issue          # Basic process uses Issue; Agile uses User Story
ADO_DEFAULT_AREA_PATH=YourProject # or YourProject\AI Working Group
ADO_PARENT_EPIC_TITLE=Electronics AI Working Group Opportunities
```

Current deployment:
- **Org:** `https://dev.azure.com/CXAEO`
- **Project:** `Opportunities`
- **Process template:** Basic (`Epic → Issue → Task`)
- **Parent Epic:** `#39 — Electronics AI Working Group Opportunities`
- **Items pushed:** Issues `#40–#78` (as of 2026-06-23 session)

---

## Implementation Files

| File | What It Does |
|---|---|
| `src/ado_client.py` | Push, sync, epic management, CLI wrapper |
| `config/ado_field_mapping.json` | ADO REST API field path reference |
| `config/mvp_output_schema.json` | Extended with 7 ADO fields |
| `.env.example` | ADO section with renewal URL and field docs |
| `src/main.py` | Step 0 (sync) + Step 9c (push) wired in |
| `src/report_generator.py` | ADO chip on cards + Progress tab HTML |
| `src/trend_reporter.py` | Progress tab injected into weekly reports |
| `src/master_exporter.py` | ADO columns AS–AY in master XLSX (with WeekDate at AR) |
| `openspec/changes/ado-pipeline-integration/` | Full OpenSpec change artifacts |

---

## Resolved Design Decisions

| Question | Decision |
|---|---|
| Work item type | `Issue` (Basic process template in `CXAEO/Opportunities`) |
| Push gate | All primary rows via explicit `--push-ado` operator action |
| Sync frequency | Every `--mode weekly` run, Step 0, before extraction |
| Dedup strategy | Title-based WIQL query before create; `ADOWorkItemId` check in memory |
| Progress tab placement | Fifth tab on weekly report; injected via `extra_nav`/`extra_section` |
| ADO state vocabulary | Basic process: `To Do`, `Doing`, `Done` (not Agile `New`/`Active`/`Resolved`) |

---

## What Remains as Future Work

- **ADO comment parsing** — pull discussion/update comments from ADO back into reports
- **Per-card push button** — UI gesture in the report to push a single row to ADO
- **Push gate filter** — only push rows at MaturitySignal ≥ "In Progress / Piloting"
- **Teams adaptive card** — notify owner when their item is pushed to ADO
- **Monthly ADO summary** — pushed / active / resolved / stalled 3+ weeks in the monthly report


---

## Problem Statement

Opportunity cards extracted from meeting transcripts mirror Azure DevOps work items closely. Currently there is no link between an identified AI opportunity and whether anyone has actually picked it up and made progress on it. When the group revisits a prior discussion ("where are we at with the invoice matching idea from May?"), there is no automated way to surface ADO status in the report.

---

## Proposed Capability

### Three sub-features

#### 1. `ado-push` — Push opportunities to ADO as work items
- Opt-in via `--push-ado` flag (never automatic)
- Each opportunity → ADO **Feature** (work item type configurable)
- Dedup guard: rows with an existing `ADOWorkItemId` are skipped
- Writes back `ADOWorkItemId`, `ADOUrl`, `ADOPushedAt` to `classified_rows.json` and master XLSX

**Field mapping (our schema → ADO):**

| Our Field | ADO Field |
|---|---|
| `Title` | `System.Title` |
| `ProblemPainPoint` + `EvidenceSummary` | `System.Description` |
| `OperatingBucket`, `MaturitySignal`, `AIUseCaseType` | Tags |
| `ValueScore` | `Microsoft.VSTS.Common.Priority` |
| `SuggestedBusinessOwnerText` | `System.AssignedTo` |
| `ProcessStage` / `SubOrdinateFunction` | `System.AreaPath` or Tags |
| `NextStep` | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| `SourceSpeaker` + `MeetingDate` | Description footer (provenance) |

#### 2. `ado-status-sync` — Pull live ADO state on each weekly run
- Auto-runs at pipeline start if any rows carry an `ADOWorkItemId`
- Pulls: `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, `ADOLastUpdated`, `ADOCommentCount`
- Stored back in `classified_rows.json` so all reports stay current without re-extraction

#### 3. `ado-progress-reporting` — "Where are we at" reporting
- **Cards tab**: ADO status chip (🔵 Active / ✅ Resolved / ⬜ New) + link to work item
- **New "Progress" tab** on weekly HTML report: groups prior-week items by ADO status, shows items that changed state since last run
- **Monthly report**: ADO summary (pushed / active / resolved / stalled 3+ weeks)

---

## Example User Journey

```
User opens weekly report → sees card for "Invoice Matching AI" raised 5/7
→ card shows: ADO #4821 · Active · Sprint 43 · Assigned: J. Smith
→ clicks "Progress" tab → sees full history:
    Week of 5/7  — Raised (Aspirational)
    Week of 6/3  — Pushed to ADO #4821
    Week of 6/10 — Status: New
    Week of 6/17 — Status: Active · Sprint 43 started
```

---

## New Files Required

| File | Purpose |
|---|---|
| `src/ado_client.py` | ADO MCP wrapper — push, sync, bulk query |
| `config/ado_field_mapping.json` | Maps schema fields → ADO internal field names |
| `config/ado_config.json` | Org, project, work item type, area path (no secrets) |
| `skills/ado_description_builder.md` | LLM skill: formats rich HTML description for ADO body |

## Schema additions (`mvp_output_schema.json`)
```json
"ADOWorkItemId":  null,
"ADOUrl":         null,
"ADOStatus":      null,
"ADOIteration":   null,
"ADOAssignedTo":  null,
"ADOLastUpdated": null,
"ADOPushedAt":    null
```

## New `.env` variables (no secrets committed)
```
ADO_ORG_URL=https://dev.azure.com/YourOrg
ADO_PROJECT=YourProject
ADO_WORK_ITEM_TYPE=Feature
ADO_DEFAULT_AREA_PATH=YourProject\AI Working Group
```

---

## Open Questions for Leadership Discussion

1. **Work item type** — Feature, User Story, or Epic?
2. **Area Path** — dedicated "AI Working Group" area, or existing product area?
3. **Push gate** — push all primary rows, or only `In Progress / Piloting` and above?
4. **ADO MCP** — is the Azure DevOps MCP server already provisioned, or does it need setup?
5. **Ownership** — who reviews/approves before push? (suggest: report author clicks "Push to ADO" per card)

---

## Implementation Path (when approved)

1. Propose as OpenSpec change `ado-work-item-integration`
2. Implement `ado_client.py` + field mapping config
3. Wire `--push-ado` flag into `main.py`
4. Add status sync step to weekly pipeline
5. Update `report_generator.py` and `trend_reporter.py` for ADO chips + Progress tab
6. Run against one week's data as pilot
