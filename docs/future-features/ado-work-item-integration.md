# Future Feature: ADO Work Item Integration

**Status**: Proposed — Pending leadership discussion  
**Logged**: 2026-06-18  
**Effort estimate**: Medium (3–5 days of implementation)

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
