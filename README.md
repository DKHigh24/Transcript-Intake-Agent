# AI Transcript Intake Agent

New operator? See `Operating Procedure/operating_manual.html` for the step-by-step manual.
System overview? See `Overview/process_overview.html` for the visual flowchart.

## Purpose

This repository contains a Python-based local agent workflow for converting Electronics
AI Working Group meeting transcripts into structured AI opportunity intake records -- and
tracking those opportunities all the way through to execution in Azure DevOps.

The core insight is that **a transcript is the beginning of the work, not the end of it**.
The agent extracts signals from discussions, classifies them, and bridges the gap between
"we talked about this" and "someone is actually working on it" by pushing opportunities
as ADO Issues and surfacing their live status in every subsequent report.

```
Meeting transcript
    |
    v  (deterministic Python)
Read -> Clean -> Chunk -> Keyword filter
    |
    v  (AI - one call per candidate)
Extract candidate opportunities
    |
    v  (AI - one call per candidate)
Classify against framework dimensions
    |
    v  (human review)
review_rows.xlsx + sharepoint_payload.json
    |
    v  (optional Power Automate)
SharePoint intake list
    |
    v  (--push-ado, opt-in, after human review)
Azure DevOps Issues  <-- closes the loop
    |
    v  (automatic, every weekly run, read-only)
Live ADO status synced back into all reports
    |
    v
"Where are we at?" answered in the Progress tab
```

---

## Operating Principles

1. **Do not send full transcripts to the model.**
   Use deterministic preprocessing -- keyword filtering, speaker-turn parsing, chunking --
   before invoking AI.

2. **AI output is draft-only.**
   All extracted rows default to `Needs Review`. The model extracts and classifies; it
   does not decide.

3. **Human review is required before records are treated as official.**
   This applies to both SharePoint records and ADO pushes.

4. **Classification and Action are different.**
   Classification use cases help us understand the work. Action use cases create, update,
   trigger, or automate a system.

5. **Preserve evidence.**
   Extracted opportunities carry speaker, timestamp, and evidence summary from the
   transcript.

6. **Optimize token usage.**
   Use Python for all deterministic work. Only send relevant, chunked text to the model.

7. **SharePoint writeback is controlled.**
   Posting to SharePoint requires a reviewed payload and a Power Automate endpoint.

8. **ADO push closes the loop -- and is always opt-in.**
   Pushing to Azure DevOps via --push-ado is never automatic. Once pushed, ADO status
   syncs back automatically every week so every report answers "where are we at" without
   manual lookups.

---

## Project Structure

```
ai-transcript-intake-agent/
|
+-- README.md
+-- requirements.txt
+-- .env.example                    # template -- copy to .env, never commit .env
+-- .gitignore
|
+-- .github/
|   +-- copilot-instructions.md
|
+-- config/
|   +-- choice_values.json          # allowed SharePoint choice values
|   +-- sharepoint_field_mapping.json
|   +-- mvp_output_schema.json      # full output row schema incl. ADO fields
|   +-- extraction_settings.json
|   +-- ado_field_mapping.json      # ADO REST API field path reference
|
+-- skills/
|   +-- extract_opportunities.md
|   +-- classify_opportunity.md
|   +-- review_rules.md
|   +-- weekly_report_format.md
|   +-- token_optimization.md
|
+-- src/
|   +-- main.py                     # pipeline orchestrator + CLI
|   +-- transcript_reader.py
|   +-- transcript_cleaner.py
|   +-- transcript_chunker.py
|   +-- candidate_detector.py       # AI extraction
|   +-- classifier.py               # AI classification
|   +-- validators.py
|   +-- review_exporter.py
|   +-- report_generator.py         # HTML reports incl. ADO chips + Progress tab
|   +-- trend_analyzer.py
|   +-- trend_reporter.py
|   +-- master_exporter.py          # Power BI flat file (XLSX, incl. ADO columns)
|   +-- history_store.py
|   +-- opportunity_matcher.py
|   +-- period_utils.py
|   +-- power_automate_client.py
|   +-- presentation_builder.py
|   +-- watch_transcripts.py        # folder watcher for auto-trigger
|   +-- ado_client.py               # Azure DevOps integration (push + sync)
|   +-- llm_client.py               # unified LLM adapter (OpenAI or Copilot SDK)
|
+-- input/
|   +-- transcripts/                # drop DOCX files here
|
+-- output/
|   +-- transcript_chunks.json      # working file -- current run
|   +-- candidates.json
|   +-- classified_rows.json
|   +-- review_rows.xlsx
|   +-- sharepoint_payload.json
|   +-- ai_opportunity_report.html
|   +-- weeks/<YYYY-MM-DD>/         # per-week archive
|   |   +-- classified_rows.json    # includes ADO fields once pushed
|   |   +-- review_rows.xlsx
|   |   +-- sharepoint_payload.json
|   |   +-- weekly_report.html      # 5 tabs: Cards/Analytics/Table/Trends/Progress
|   +-- history/
|   |   +-- opportunities.json      # cumulative cross-week opportunity history
|   +-- reports/
|   |   +-- monthly_<YYYY-MM>.html  # rolling monthly trend rollup
|   +-- meeting_presentations/
|       +-- Session_N_<date>.pptx
|
+-- Overview/
|   +-- process_overview.html       # visual flowchart + stage table
|   +-- open_overview.ps1
|
+-- Operating Procedure/
|   +-- operating_manual.html       # step-by-step operator manual
|
+-- docs/
    +-- future-features/            # proposed capabilities not yet implemented
```

---

## End-to-End Pipeline (--mode weekly)

### Step 0 -- ADO Status Sync (automatic, read-only)

Before any new extraction, the pipeline queries Azure DevOps and updates `ADOStatus`,
`ADOIteration`, `ADOAssignedTo`, and `ADOLastUpdated` across every archived
`classified_rows.json`. This ensures the Progress tab reflects live ADO state, not
just the state at push time.

Skipped silently if `ADO_PAT` is absent. Never creates or modifies ADO items.

### Step 1 -- Read Transcript

Reads the `.docx` transcript from `input/transcripts/`.

### Step 2 -- Clean Transcript

Normalizes text while preserving speaker turns and timestamps.

### Step 3 -- Chunk Transcript

Filters speaker turns using candidate keywords and packs them into smaller chunks
to minimize token usage.

### Step 4 -- Extract Candidates (AI)

The model identifies AI opportunity signals: demos, KB candidates, access/governance
issues, cost observations, tool patterns, and reusable workflows.

### Step 4b -- Deduplicate Candidates

Deterministic fuzzy-match pass removes near-duplicates before classification.

### Step 5 -- Classify Candidates (AI)

Each candidate is mapped into the full AI Acceleration SharePoint schema.
One model call per candidate.

### Step 5b -- Validate + Confidence Filter

Rows validated against allowed choice values. Low-confidence rows routed to Triage.

### Step 6 -- Export Review Workbook

Human-reviewable `output/review_rows.xlsx`.

### Step 7 -- Build SharePoint Payload

`output/sharepoint_payload.json` using internal field mappings.

### Step 8 -- Generate HTML Report

`output/ai_opportunity_report.html` with Cards, Analytics, and Full Table tabs.

### Step 9 -- Archive Week

Outputs copied to `output/weeks/<YYYY-MM-DD>/`.

### Step 9b -- Update Master Workbook

`output/master_opportunities.xlsx` updated. This is the Power BI source file.
Includes all classification fields plus seven ADO tracking columns (AR-AX):
ADOWorkItemId, ADOUrl, ADOStatus, ADOAssignedTo, ADOIteration, ADOLastUpdated, ADOPushedAt.

If the file is open in Excel, the pipeline warns and continues. Close it and re-run
`--mode rebuild` to pick up the new rows.

### Step 9c -- Push to ADO (opt-in, --push-ado flag only)

**This is the step that closes the loop.**

When --push-ado is passed, every primary row without an ADOWorkItemId is created as
an Issue in ADO under the configured parent Epic. The item receives:

- Title from the Title field
- Description: rich HTML with problem statement, evidence quote, speaker, timestamp,
  meeting date, next step, and classification metadata table
- Tags: AI Working Group; Transcript Intake; MaturitySignal; OperatingBucket;
  AIUseCaseType; ProcessStage
- Parent relation to the Epic set in ADO_PARENT_EPIC_TITLE

After creation, ADOWorkItemId, ADOUrl, ADOStatus, and ADOPushedAt are written back
to the archived classified_rows.json. Every future weekly run's Step 0 sync will
pick up live status automatically.

**Dedup guard:** Before creating a new item, the client queries ADO by title. If an
item with that exact title already exists, it recovers the existing ID. Safe to re-run.

### Step 10 -- Ingest into History

Rows merged into `output/history/opportunities.json` using deterministic fuzzy
matching. Re-runs for the same meeting date are idempotent.

### Step 11 -- Generate Weekly + Monthly Reports

**Weekly report** (`output/weeks/<YYYY-MM-DD>/weekly_report.html`) -- five tabs:

| Tab | Contents |
|-----|----------|
| Cards | Opportunity cards with ADO chip (colored state badge + live link) on pushed items; filterable by bucket, type, signal, and MaturitySignal |
| Analytics | Charts including MaturitySignal donut |
| Table | Full row view |
| Trends | New vs. carried-over; week-over-week signal/level movement; per-week trend line |
| Progress | All historical ADO-linked items grouped by current ADO state (Doing / To Do / Done); highlights items that moved state in the last 7 days; answers "where are we at with X we discussed weeks ago?" |

**Monthly report** (`output/reports/monthly_<YYYY-MM>.html`):
- Unique opportunity count, weeks covered, new vs. carried-from-prior
- Per-week stacked bucket distribution
- Signal/level momentum (escalations)
- Full table with first-seen, last-seen, and hit counts

### Step 12 -- Generate Presentation

Upcoming-session PPTX at `output/meeting_presentations/`.

---

## How to Run

### Standard weekly run (no ADO push)

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe src\main.py `
  --input "input/transcripts/Electronics AI - Working Session - 6_17_2026.docx" `
  --mode weekly
```

### Weekly run + push new opportunities to ADO

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe src\main.py `
  --input "input/transcripts/Electronics AI - Working Session - 6_17_2026.docx" `
  --mode weekly --push-ado
```

Use --push-ado after reviewing `output/weeks/<date>/review_rows.xlsx`. The push is
permanent -- ADO items created here will be tracked from this point forward.

### Rebuild all reports (no transcript needed)

```powershell
.\.venv\Scripts\python.exe src\main.py --mode rebuild
```

Use after report template changes, after closing Excel for master workbook refresh,
or after manual history edits.

### Build or refresh a monthly report

```powershell
.\.venv\Scripts\python.exe src\main.py --mode monthly --month 2026-06
```

### Sync ADO statuses only (no pipeline run)

```powershell
.\.venv\Scripts\python.exe src\ado_client.py --sync
```

### Push rows from latest classified_rows.json to ADO

```powershell
.\.venv\Scripts\python.exe src\ado_client.py --push-all
```

### Additional flags

| Flag | Description |
|------|-------------|
| --mock | Skip AI calls for pipeline wiring tests |
| --date YYYY-MM-DD | Override the meeting date parsed from the filename |
| --include-low-confidence | Include low-confidence rows in primary output instead of triage |

---

## Azure DevOps Integration -- Closing the Loop

### Why ADO?

Identified AI opportunities don't deliver value unless someone picks them up and
executes. Without a link to a work tracking system, the group cannot answer "we
talked about invoice matching automation three weeks ago -- has anything happened?"

The ADO integration closes that loop by:

1. Pushing each reviewed opportunity to ADO as a tracked Issue under a shared Epic
2. Syncing live ADO status (To Do / Doing / Done, iteration, assignee) back into
   every report at the start of each weekly run
3. Surfacing that status in a dedicated Progress tab on the weekly HTML report,
   grouped by state, highlighting items that moved in the past 7 days

### Configuration (.env)

```
# Azure DevOps
ADO_ORG_URL=https://dev.azure.com/YourOrg
ADO_PROJECT=YourProject
ADO_PAT=your-personal-access-token
# Token renewal: https://dev.azure.com/YourOrg/_usersSettings/tokens
# Required scopes: Work Items (Read & Write)

ADO_WORK_ITEM_TYPE=Issue
ADO_DEFAULT_AREA_PATH=YourProject
ADO_PARENT_EPIC_TITLE=Electronics AI Working Group Opportunities
```

Never commit .env. ADO_PAT is a secret.

### ADO field mapping

| Our Field | ADO Field |
|-----------|-----------|
| Title | System.Title |
| ProblemPainPoint + EvidenceSummary + NextStep + metadata | System.Description (rich HTML) |
| MaturitySignal, OperatingBucket, AIUseCaseType, ProcessStage | System.Tags |
| Project/area config | System.AreaPath |
| Parent Epic | System.LinkTypes.Hierarchy-Reverse |

### ADO tracking fields

| Field | Description |
|-------|-------------|
| ADOWorkItemId | Integer ADO Issue ID (null until pushed) |
| ADOUrl | Direct browser link to the work item |
| ADOStatus | Current state: To Do / Doing / Done (Basic process) |
| ADOIteration | Sprint or iteration path |
| ADOAssignedTo | Display name of the assigned team member |
| ADOLastUpdated | ISO timestamp of last ADO state change |
| ADOPushedAt | ISO timestamp when this agent first pushed the item |

### Weekly sync behavior

Every --mode weekly run begins with a read-only bulk GET to ADO. All archived weeks
are scanned for ADOWorkItemId values, deduplicated, batched (up to 200 per request),
and updated in a single round-trip. Silent on success; warns on failure; never blocks
the pipeline.

---

## Weekly and Monthly Trend Analysis

### How a week is identified

Meeting date is parsed from the transcript filename:
`Electronics AI - Working Session - 6_3_2026.docx` -> 2026-06-03

Supported formats: M_D_YYYY, M-D-YYYY, YYYY-MM-DD, M.D.YY.
Override with --date YYYY-MM-DD if needed.

### Back-dated transcripts

If the new transcript date is earlier than the latest date in history, the pipeline
automatically rebuilds ALL weekly and monthly reports. No special flag needed.

### Folder watcher (automatic processing)

```powershell
# Baseline existing files so they are not re-run
python src/watch_transcripts.py --mark-processed

# Start watching
python src/watch_transcripts.py
```

The watcher polls `input/transcripts/` and triggers --mode weekly on each new .docx
once its upload is stable. Processed files are tracked in
`output/history/processed_files.json`.

The watcher does NOT pass --push-ado automatically. ADO push always requires explicit
operator action after review.

---

## AI Acceleration Classification Framework

### AI Use Case Type

| Value | Description |
|-------|-------------|
| Classification | AI helps understand the work (summarize, analyze, categorize) |
| Action | AI performs or changes the work (create, update, trigger, send) |
| Both | The workflow both interprets and produces output or action |
| Unknown / Needs Review | Default when unclear |

### Operating Buckets

```
Outside / Pre-Sale
Inside / Pre-Sale
Manufacturing
Post Shipment
Cross-Functional / Governance
Unknown / Needs Review
```

### Levels of Analysis

| Level | Label | Description |
|-------|-------|-------------|
| 0 | Signal Capture | Mentioned but not yet mature |
| 1 | Categorization | Main value is organizing into taxonomy |
| 2 | Descriptive Analysis | AI summarizes what happened |
| 3 | Diagnostic Analysis | AI explains why something is happening |
| 4 | Predictive / Risk | AI identifies likely future risk |
| 5 | Prescriptive | AI recommends what should happen next |
| 6 | Action / Automation | AI creates, updates, triggers, or automates |
| 7 | Release Candidate | Mature enough for pilot / KB / leadership demo |

### MaturitySignal

```
Aspirational / Not Started
Exploring / Experimenting
In Progress / Piloting
Deployed / In Use
Unknown / Needs Review
```

### Signal Strength

```
Isolated Example
Repeated Within One Team
Repeated Across Multiple Teams
Cross-Functional Pattern
Leadership Priority
Unknown / Needs Review
```

---

## Output Row Schema

Each classified row contains the fields below. ADO fields default to null until
--push-ado is run.

| Field | Default / Source |
|-------|-----------------|
| Title | From transcript |
| ProblemPainPoint | From transcript |
| RequestingTeam | From transcript |
| CurrentStatus | (2) Needs Review |
| Priority | High |
| OperatingBucket | Classified |
| ProcessStage | Classified |
| SubOrdinateFunction | Classified |
| UpstreamDownstreamImpact | Classified |
| AIUseCaseType | Classified |
| PrimaryFunctionChoice | Classified |
| LevelOfAnalysis | Classified |
| MaturitySignal | Classified |
| SignalStrength | Classified |
| FrequencyOfPainPoint | Classified |
| ManualEffortLevel | Classified |
| Repeatability | Classified |
| ScalabilityPotential | Classified |
| ValueScore | 1-5 |
| EffortScore | 1-5 |
| RiskScore | 1-5 |
| ReadinessScore | 1-5 |
| SignalScore | 1-5 |
| PrimaryTool | Classified |
| PrimaryDataSource | Meeting Transcript |
| IntegrationNeeded | false |
| DataSensitivity | Internal |
| HumanReviewRequired | true |
| HumanInTheLoopRequired | true |
| AutomationRisk | Classified |
| SecurityAccessConcern | false |
| LegalComplianceConcern | false |
| GuardrailsNeeded | AI-generated |
| SuggestedBusinessOwnerText | AI-inferred |
| SuggestedTechnicalOwnerText | AI-inferred |
| SuggestedSMEChampionText | AI-inferred |
| NextStep | AI-generated |
| ScheduleHealth | Not Started |
| EvidenceSummary | From transcript |
| SourceSpeaker | From transcript |
| SourceTimestamp | From transcript |
| ConfidenceLevel | High / Medium / Low |
| ADOWorkItemId | null (until --push-ado) |
| ADOUrl | null (until --push-ado) |
| ADOStatus | null (until sync runs) |
| ADOIteration | null (until sync runs) |
| ADOAssignedTo | null (until sync runs) |
| ADOLastUpdated | null (until sync runs) |
| ADOPushedAt | null (until --push-ado) |

---

## Setup

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in your values.
See the Azure DevOps section above for ADO-specific variables.

---

## Human Review Rules

Before any row is pushed to SharePoint or ADO:

| Field | Review Question |
|-------|----------------|
| Title | Accurate and specific? |
| ProblemPainPoint | Clearly describes the real pain? |
| EvidenceSummary | Grounded in what was actually said? |
| SourceSpeaker / Timestamp | Traceable to the transcript? |
| OperatingBucket | Correct business area? |
| AIUseCaseType | Classification, Action, or Both? |
| LevelOfAnalysis | Matches what was described? |
| MaturitySignal | Honest about how mature this actually is? |
| GuardrailsNeeded | Right risks called out? |
| NextStep | Actionable and realistic? |
| SuggestedOwners | Real people and correct teams? |
| ADO push | Row fully reviewed before pushing? |

Do not trust model output without human validation.

---

## Governance Rules

- Rows always default to Needs Review.
- The model extracts and classifies. It cannot approve.
- --push-ado is always opt-in and always follows human review.
- Step 0 ADO sync is read-only. It never creates or modifies ADO items automatically.
- Power Automate push is disabled by default (ENABLE_POWER_AUTOMATE_PUSH=false).
- master_opportunities.xlsx is the Power BI source -- close it in Excel before a rebuild.

---

## Future Enhancements

```
Duplicate detection against existing SharePoint items
Automatic enrichment of existing SharePoint rows
KB article candidate detection and draft creation
Solution Registry integration
Teams adaptive card approval workflow
ADO comment parsing (pull discussion updates back into reports)
Power BI dataset push trigger
Owner / SME notification on new push
```

See `docs/future-features/` for detailed proposals.

---

## Success Criteria

```
[x] Read a DOCX transcript
[x] Extract relevant chunks without sending the full transcript to AI
[x] Produce candidate AI opportunities with evidence
[x] Classify opportunities into the full SharePoint schema
[x] Generate a human-reviewable workbook
[x] Generate a SharePoint-ready JSON payload
[x] Optionally post draft rows to Power Automate
[x] Archive each week and build trend reports week-over-week
[x] Push approved opportunities to Azure DevOps as tracked Issues
[x] Sync live ADO status back into reports automatically
[x] Answer "where are we at?" for any prior discussion via the Progress tab
[x] Preserve evidence, traceability, and human review at every step
```

---

## Important Guardrail

This agent is an intake assistant and a progress tracker -- not a decision-maker.

It can extract, classify, suggest, push, sync, and report. It cannot approve, publish,
or finalize AI opportunities without a human in the loop.
