# Transcript-Intake-Agent
Python agent that extracts AI opportunities from meeting transcripts, classifies them into the AI Acceleration framework, generates reviewable outputs, optionally posts draft intake records through Power Automate, and â€” to **close the loop on where the work actually occurs** â€” pushes approved opportunities to Azure DevOps as tracked work items and syncs their live status back into every weekly report.

# AI Transcript Intake Agent

> ðŸ“‹ **New operator?** See [`Operating Procedure/operating_manual.html`](Operating%20Procedure/operating_manual.html) for the full step-by-step manual.
> ðŸ“– **System overview?** See [`Overview/process_overview.html`](Overview/process_overview.html) for the visual flowchart.

## Purpose

This repository contains a Python-based local agent workflow for converting Electronics AI Working Group meeting transcripts into structured AI opportunity intake records â€” and tracking those opportunities all the way through to execution in Azure DevOps.

The core insight is that **a transcript is the beginning of the work, not the end of it**. The agent extracts signals from discussions, classifies them, and then bridges the gap between *"we talked about this"* and *"someone is actually working on it"* by pushing opportunities as ADO Issues and surfacing their live status in every subsequent report.

```text
Meeting transcript
    â†“
AI opportunity extraction  (AI)
    â†“
Classification against defined dimensions  (AI)
    â†“
Human review
    â†“
SharePoint intake list  (optional Power Automate)
    â†“
Azure DevOps work items  (--push-ado)  â† closes the loop
    â†“
Live ADO status synced back every week  (automatic)
    â†“
"Where are we at?" answered in the Progress tab of every report
```

> ðŸ“– **New here?** See **[`Overview/process_overview.html`](Overview/process_overview.html)**
> for a visual flowchart of the whole process. Open it with
> `./Overview/open_overview.ps1` or `Invoke-Item "Overview/process_overview.html"`.

---

## Operating Principles

1. **Do not send full transcripts to the model.**
   Use deterministic preprocessing â€” keyword filtering, speaker-turn parsing, chunking â€” before invoking AI.

2. **AI output is draft-only.**
   All extracted rows default to `Needs Review`. The model extracts and classifies; it does not decide.

3. **Human review is required before records are treated as official.**
   This applies to both SharePoint records and ADO pushes.

4. **Classification and Action are different.**
   Classification use cases help us understand the work. Action use cases create, update, trigger, or automate a system.

5. **Preserve evidence.**
   Extracted opportunities carry speaker, timestamp, and evidence summary from the transcript.

6. **Optimize token usage.**
   Use Python for all deterministic work. Only send relevant, chunked text to the model.

7. **SharePoint writeback is controlled.**
   Posting to SharePoint requires a reviewed payload and a Power Automate endpoint.

8. **ADO push closes the loop â€” and is always opt-in.**
   Pushing to Azure DevOps via `--push-ado` is never automatic. Once pushed, ADO status syncs back automatically every week so every report answers "where are we at" without manual updates.

---

## Project Structure

```text
ai-transcript-intake-agent/
â”‚
â”œâ”€â”€ README.md
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .env.example                    # template â€” copy to .env, never commit .env
â”œâ”€â”€ .gitignore
â”‚
â”œâ”€â”€ .github/
â”‚   â””â”€â”€ copilot-instructions.md
â”‚
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ choice_values.json          # allowed SharePoint choice values
â”‚   â”œâ”€â”€ sharepoint_field_mapping.json
â”‚   â”œâ”€â”€ mvp_output_schema.json      # full output row schema incl. ADO fields
â”‚   â”œâ”€â”€ extraction_settings.json
â”‚   â””â”€â”€ ado_field_mapping.json      # ADO REST API field path reference
â”‚
â”œâ”€â”€ skills/
â”‚   â”œâ”€â”€ extract_opportunities.md
â”‚   â”œâ”€â”€ classify_opportunity.md
â”‚   â”œâ”€â”€ review_rules.md
â”‚   â”œâ”€â”€ weekly_report_format.md
â”‚   â””â”€â”€ token_optimization.md
â”‚
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ main.py                     # pipeline orchestrator + CLI
â”‚   â”œâ”€â”€ transcript_reader.py
â”‚   â”œâ”€â”€ transcript_cleaner.py
â”‚   â”œâ”€â”€ transcript_chunker.py
â”‚   â”œâ”€â”€ candidate_detector.py       # AI extraction
â”‚   â”œâ”€â”€ classifier.py               # AI classification
â”‚   â”œâ”€â”€ validators.py
â”‚   â”œâ”€â”€ review_exporter.py
â”‚   â”œâ”€â”€ report_generator.py         # HTML reports incl. ADO chips + Progress tab
â”‚   â”œâ”€â”€ trend_analyzer.py
â”‚   â”œâ”€â”€ trend_reporter.py
â”‚   â”œâ”€â”€ master_exporter.py          # Power BI flat file (XLSX, incl. ADO columns)
â”‚   â”œâ”€â”€ history_store.py
â”‚   â”œâ”€â”€ opportunity_matcher.py
â”‚   â”œâ”€â”€ period_utils.py
â”‚   â”œâ”€â”€ power_automate_client.py
â”‚   â”œâ”€â”€ presentation_builder.py
â”‚   â”œâ”€â”€ watch_transcripts.py        # folder watcher for auto-trigger
â”‚   â”œâ”€â”€ ado_client.py               # Azure DevOps integration (push + sync)
â”‚   â””â”€â”€ llm_client.py               # unified LLM adapter (OpenAI or Copilot SDK)
â”‚
â”œâ”€â”€ input/
â”‚   â””â”€â”€ transcripts/                # drop DOCX files here
â”‚
â”œâ”€â”€ output/
â”‚   â”œâ”€â”€ transcript_chunks.json      # working file â€” current run
â”‚   â”œâ”€â”€ candidates.json
â”‚   â”œâ”€â”€ classified_rows.json
â”‚   â”œâ”€â”€ review_rows.xlsx
â”‚   â”œâ”€â”€ sharepoint_payload.json
â”‚   â”œâ”€â”€ ai_opportunity_report.html
â”‚   â”œâ”€â”€ weeks/<YYYY-MM-DD>/         # per-week archive
â”‚   â”‚   â”œâ”€â”€ classified_rows.json    # includes ADO fields once pushed
â”‚   â”‚   â”œâ”€â”€ review_rows.xlsx
â”‚   â”‚   â”œâ”€â”€ sharepoint_payload.json
â”‚   â”‚   â””â”€â”€ weekly_report.html      # Cards / Analytics / Table / Trends / Progress
â”‚   â”œâ”€â”€ history/
â”‚   â”‚   â””â”€â”€ opportunities.json      # cumulative cross-week opportunity history
â”‚   â”œâ”€â”€ reports/
â”‚   â”‚   â””â”€â”€ monthly_<YYYY-MM>.html  # rolling monthly trend rollup
â”‚   â””â”€â”€ meeting_presentations/
â”‚       â””â”€â”€ Session_N_<date>.pptx   # upcoming session deck
â”‚
â”œâ”€â”€ Overview/
â”‚   â”œâ”€â”€ process_overview.html       # visual flowchart + stage table
â”‚   â””â”€â”€ open_overview.ps1
â”‚
â”œâ”€â”€ Operating Procedure/
â”‚   â””â”€â”€ operating_manual.html       # step-by-step operator manual
â”‚
â””â”€â”€ docs/
    â””â”€â”€ future-features/            # proposed but not-yet-implemented capabilities
```

---

## End-to-End Pipeline

The full pipeline runs when you execute `--mode weekly`. Here is every step in order:

### Step 0 â€” ADO Status Sync *(automatic, read-only)*

Before any new extraction begins, the pipeline queries Azure DevOps and updates the `ADOStatus`, `ADOIteration`, `ADOAssignedTo`, and `ADOLastUpdated` fields across every archived `classified_rows.json` file. This ensures the Progress tab in every report reflects what is happening right now in ADO â€” not just what was true when an item was first pushed.

> This step runs silently and is skipped if `ADO_PAT` is not set in `.env`. It never creates or modifies ADO items â€” it only reads.

### Step 1 â€” Read Transcript

The agent reads a `.docx` meeting transcript from `input/transcripts/`.

### Step 2 â€” Clean Transcript

The transcript is normalized while preserving speaker turns and timestamps.

### Step 3 â€” Chunk Transcript

Speaker turns are filtered using candidate keywords and packed into smaller chunks to minimize token usage.

### Step 4 â€” Extract Candidates *(AI)*

The model identifies AI opportunity signals: demos, KB candidates, access/governance issues, cost observations, tool patterns, and reusable workflows.

### Step 4b â€” Deduplicate Candidates

A deterministic fuzzy-match pass removes near-duplicate candidates before classification.

### Step 5 â€” Classify Candidates *(AI)*

Each candidate is mapped into the full AI Acceleration SharePoint schema â€” one model call per candidate.

### Step 5b â€” Validate + Confidence Filter

Rows are validated against allowed choice values. Low-confidence rows are routed to a Triage sheet rather than the primary output.

### Step 6 â€” Export Review Workbook

A human-reviewable `.xlsx` workbook is created at `output/review_rows.xlsx`.

### Step 7 â€” Build SharePoint Payload

A SharePoint-ready JSON payload is written to `output/sharepoint_payload.json`.

### Step 8 â€” Generate HTML Report

`output/ai_opportunity_report.html` is produced with:
- **ðŸ“‹ Opportunity Cards** â€” filterable by bucket, type, signal, and MaturitySignal
- **ðŸ“Š Analytics** â€” donut and bar charts; MaturitySignal distribution
- **ðŸ—‚ Full Table** â€” sortable complete row view

### Step 9 â€” Archive Week

The week's outputs are copied to `output/weeks/<YYYY-MM-DD>/`.

### Step 9b â€” Update Master Workbook

`output/master_opportunities.xlsx` is updated with the new week's rows. This is the Power BI source file. Columns include all classification fields **plus** the seven ADO tracking columns (ARâ€“AX): `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, `ADOAssignedTo`, `ADOIteration`, `ADOLastUpdated`, `ADOPushedAt`.

> If the file is open in Excel, the pipeline warns and continues â€” close it and re-run `--mode rebuild` to pick up the new rows.

### Step 9c â€” Push to ADO *(opt-in, `--push-ado` flag only)*

**This is the step that closes the loop.**

When `--push-ado` is passed, the pipeline pushes every primary row (that does not already have an `ADOWorkItemId`) to Azure DevOps as an **Issue** under the configured parent Epic. The ADO item receives:

- **Title** from `Title`
- **Description** â€” rich HTML including problem statement, evidence quote, speaker, timestamp, meeting date, next step, and classification metadata
- **Tags** â€” `AI Working Group; Transcript Intake; <MaturitySignal>; <OperatingBucket>; <AIUseCaseType>; <ProcessStage>`
- **Parent relation** to the Epic `ADO_PARENT_EPIC_TITLE`

After creation, `ADOWorkItemId`, `ADOUrl`, `ADOStatus`, and `ADOPushedAt` are written back to the archived `classified_rows.json`. This means every future weekly run's Step 0 sync will pick up live status for these items automatically.

**Dedup guard:** If `--push-ado` is run a second time on the same week (or if titles match items already in ADO), the client recovers the existing work item ID rather than creating a duplicate.

### Step 10 â€” Ingest into History

The week's rows are merged into `output/history/opportunities.json` using deterministic fuzzy matching. Re-runs for the same meeting date are idempotent.

### Step 11 â€” Generate Weekly + Monthly Reports

The final HTML reports are built:

**Weekly report** (`output/weeks/<YYYY-MM-DD>/weekly_report.html`) contains five tabs:
- **ðŸ“‹ Cards** â€” opportunity cards with ADO chip (colored state badge + live link) on every pushed item
- **ðŸ“Š Analytics** â€” charts including MaturitySignal donut
- **ðŸ—‚ Table** â€” full row view
- **ðŸ“ˆ Trends** â€” new vs. carried-over, week-over-week signal/level movement, per-week trend line
- **ðŸ”„ Progress** â€” groups all historical ADO-linked items by current ADO state (Doing / To Do / Done); highlights items that moved state within the last 7 days; answers *"where are we at with X that we discussed weeks ago?"*

**Monthly report** (`output/reports/monthly_<YYYY-MM>.html`) provides:
- Unique opportunity count, weeks covered, new vs. carried-from-prior
- Per-week stacked bucket distribution
- Signal/level momentum table (escalations)
- Full table with first-seen, last-seen, and hit counts

### Step 12 â€” Generate Presentation

An upcoming-session PowerPoint deck is built at `output/meeting_presentations/`.

---

## How to Run

### Standard weekly run (no ADO push)

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe src\main.py --input "input/transcripts/Electronics AI - Working Session - 6_17_2026.docx" --mode weekly
```

### Weekly run + push new opportunities to ADO

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe src\main.py --input "input/transcripts/Electronics AI - Working Session - 6_17_2026.docx" --mode weekly --push-ado
```

> **When to use `--push-ado`:** After you have reviewed `output/weeks/<date>/review_rows.xlsx` and are satisfied that the extracted opportunities are accurate. The push is permanent â€” ADO items created here will be tracked from this point forward.

### Rebuild all reports (no transcript needed)

```powershell
.\.venv\Scripts\python.exe src\main.py --mode rebuild
```

Use this after changes to report templates, after closing Excel and needing to refresh the master workbook, or after manual history edits.

### Build/refresh a monthly report

```powershell
.\.venv\Scripts\python.exe src\main.py --mode monthly --month 2026-06
```

### Sync ADO statuses only (no pipeline run)

```powershell
.\.venv\Scripts\python.exe src\ado_client.py --sync
```

### Push all rows from the latest classified_rows.json to ADO

```powershell
.\.venv\Scripts\python.exe src\ado_client.py --push-all
```

### Other flags

```text
--mock           skip AI calls for testing pipeline wiring
--date YYYY-MM-DD  override the meeting date parsed from the filename
--include-low-confidence  include low-confidence rows in primary output (not triage)
```

---

## Azure DevOps Integration â€” Closing the Loop

### Why ADO?

Identified AI opportunities don't deliver value unless someone picks them up and executes. Without a link between a transcript discussion and a work tracking system, the group has no way to answer *"we talked about invoice matching automation three weeks ago â€” has anything happened?"*

The ADO integration closes that loop by:
1. **Pushing** each reviewed opportunity to ADO as a tracked Issue under a shared Epic
2. **Syncing** live ADO status (To Do / Doing / Done, iteration, assignee) back into every report at the start of each weekly run
3. **Surfacing** that status in a dedicated **Progress tab** on the weekly HTML report, grouped by state and highlighting items that moved in the past 7 days

### Configuration (`.env`)

```env
# â”€â”€ Azure DevOps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ADO_ORG_URL=https://dev.azure.com/YourOrg
ADO_PROJECT=YourProject
ADO_PAT=your-personal-access-token
# Token renewal: https://dev.azure.com/YourOrg/_usersSettings/tokens
# Required scopes: Work Items (Read & Write)

ADO_WORK_ITEM_TYPE=Issue          # Basic process: Issue; Agile: User Story
ADO_DEFAULT_AREA_PATH=YourProject # or YourProject\AI Working Group
ADO_PARENT_EPIC_TITLE=Electronics AI Working Group Opportunities
```

> **Never commit `.env`** â€” it is gitignored. ADO_PAT is a secret.

### ADO field mapping

| Our Field | ADO Field |
|---|---|
| `Title` | `System.Title` |
| `ProblemPainPoint` + `EvidenceSummary` + `NextStep` + metadata | `System.Description` (rich HTML) |
| `MaturitySignal`, `OperatingBucket`, `AIUseCaseType`, `ProcessStage` | `System.Tags` |
| Project/area config | `System.AreaPath` |
| Parent Epic | `System.LinkTypes.Hierarchy-Reverse` relation |

### ADO tracking fields in `classified_rows.json` and master XLSX

| Field | Description |
|---|---|
| `ADOWorkItemId` | Integer ID of the ADO Issue (null until pushed) |
| `ADOUrl` | Direct browser link to the work item |
| `ADOStatus` | Current state: `To Do`, `Doing`, `Done` (Basic); `New`, `Active`, `Resolved` (Agile) |
| `ADOIteration` | Sprint or iteration path |
| `ADOAssignedTo` | Display name of the assigned team member |
| `ADOLastUpdated` | ISO timestamp of last state change |
| `ADOPushedAt` | ISO timestamp when item was first pushed from this agent |

### Weekly sync behavior

Every `--mode weekly` run begins with a read-only bulk GET to ADO. All archived weeks are scanned for `ADOWorkItemId` values, deduplicated, batched (up to 200 per request), and updated in a single round-trip. The sync is silent on success and warns on failure without blocking the pipeline.

---

## Weekly & Monthly Trend Analysis

The agent supports recurring **weekly transcript uploads**. Each week's transcript is processed, archived, and merged into a cumulative history so the system can look back over previous weeks and surface trends.

### How a week is identified

The meeting date is parsed from the transcript filename
(e.g. `Electronics AI - Working Session - 6_3_2026.docx` â†’ `2026-06-03`).
Supported formats: `M_D_YYYY`, `M-D-YYYY`, `YYYY-MM-DD`, `M.D.YY`.
Override with `--date YYYY-MM-DD` if needed.

### Back-dated transcripts

If the new transcript's date is earlier than (or equal to) the latest date already in history, the pipeline automatically rebuilds **all** weekly and monthly reports so longitudinal views stay accurate. No special flag is needed.

### Folder watcher (automatic processing)

```powershell
# Baseline existing files so they are not re-run
python src/watch_transcripts.py --mark-processed

# Start watching â€” processes any new .docx automatically
python src/watch_transcripts.py
```

The watcher polls `input/transcripts/` and triggers `--mode weekly` on each new file once its upload is stable (size + mtime unchanged for one full poll interval). Processed files are tracked in `output/history/processed_files.json`.

> The watcher does **not** pass `--push-ado` automatically. ADO push always requires explicit operator action after review.

---

## AI Acceleration Classification Framework

### AI Use Case Type

```text
Classification   â€” AI helps understand the work (summarize, analyze, categorize)
Action           â€” AI performs or changes the work (create, update, trigger, send)
Both             â€” the workflow both interprets AND produces output or action
Unknown / Needs Review
```

### Operating Buckets

```text
Outside / Pre-Sale
Inside / Pre-Sale
Manufacturing
Post Shipment
Cross-Functional / Governance
Unknown / Needs Review
```

### Levels of Analysis

```text
Level 0 â€” Signal Capture         mentioned but not yet mature
Level 1 â€” Categorization         main value is organizing into taxonomy
Level 2 â€” Descriptive Analysis   AI summarizes what happened
Level 3 â€” Diagnostic Analysis    AI explains why something is happening
Level 4 â€” Predictive / Risk      AI identifies likely future risk
Level 5 â€” Prescriptive           AI recommends what should happen next
Level 6 â€” Action / Automation    AI creates, updates, triggers, or automates
Level 7 â€” Release Candidate      mature enough for pilot / KB / leadership demo
```

### MaturitySignal

```text
Aspirational / Not Started
Exploring / Experimenting
In Progress / Piloting
Deployed / In Use
Unknown / Needs Review
```

### Signal Strength

```text
Isolated Example
Repeated Within One Team
Repeated Across Multiple Teams
Cross-Functional Pattern
Leadership Priority
Unknown / Needs Review
```

---

## Schema â€” Row Fields

Each classified row includes all of the following. ADO fields default to `null` until `--push-ado` is run.

| Field | Description |
|---|---|
| `Title` | Short descriptive title |
| `ProblemPainPoint` | The pain or inefficiency described |
| `RequestingTeam` | Team that raised the topic |
| `CurrentStatus` | Default: `(2) Needs Review` |
| `Priority` | High / Medium / Low |
| `OperatingBucket` | One of the defined buckets |
| `ProcessStage` | Where in the business process |
| `SubOrdinateFunction` | Sub-function within the stage |
| `UpstreamDownstreamImpact` | Scope of impact |
| `AIUseCaseType` | Classification / Action / Both |
| `PrimaryFunctionChoice` | Primary AI function |
| `LevelOfAnalysis` | Level 0â€“7 |
| `MaturitySignal` | Current maturity of the opportunity |
| `SignalStrength` | How broadly the need is shared |
| `FrequencyOfPainPoint` | How often the pain occurs |
| `ManualEffortLevel` | Effort currently required manually |
| `Repeatability` | How repeatable the task is |
| `ScalabilityPotential` | How broadly this could scale |
| `ValueScore` | 1â€“5 |
| `EffortScore` | 1â€“5 (lower = less effort) |
| `RiskScore` | 1â€“5 |
| `ReadinessScore` | 1â€“5 |
| `SignalScore` | 1â€“5 |
| `PrimaryTool` | Primary tool implicated |
| `PrimaryDataSource` | Default: `Meeting Transcript` |
| `IntegrationNeeded` | bool |
| `DataSensitivity` | Default: `Internal` |
| `HumanReviewRequired` | Default: `true` |
| `HumanInTheLoopRequired` | Default: `true` |
| `AutomationRisk` | Risk classification |
| `SecurityAccessConcern` | bool |
| `LegalComplianceConcern` | bool |
| `GuardrailsNeeded` | Free-text guardrail description |
| `SuggestedBusinessOwnerText` | Suggested owner (not confirmed) |
| `SuggestedTechnicalOwnerText` | Suggested technical owner |
| `SuggestedSMEChampionText` | Suggested SME |
| `NextStep` | Recommended next action |
| `ScheduleHealth` | Default: `Not Started` |
| `EvidenceSummary` | Quote/paraphrase from transcript |
| `SourceSpeaker` | Speaker who raised it |
| `SourceTimestamp` | Timestamp in the transcript |
| `ConfidenceLevel` | High / Medium / Low |
| `ADOWorkItemId` | ADO Issue ID (null until pushed) |
| `ADOUrl` | Direct link to ADO item |
| `ADOStatus` | Live ADO state |
| `ADOIteration` | Sprint/iteration |
| `ADOAssignedTo` | Assigned team member |
| `ADOLastUpdated` | Last state change timestamp |
| `ADOPushedAt` | When pushed from this agent |

---

## Setup

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate        # Windows
# source .venv/bin/activate     # Mac/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in:

```env
# â”€â”€ LLM Backend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Option A: GitHub Copilot SDK (preferred if you have Copilot access)
GITHUB_TOKEN=your-github-personal-access-token

# Option B: OpenAI API
# OPENAI_API_KEY=your-openai-key

# â”€â”€ Power Automate (optional) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
POWER_AUTOMATE_URL=https://replace-with-your-flow-url
ENABLE_POWER_AUTOMATE_PUSH=false

# â”€â”€ Azure DevOps (required for --push-ado and ADO sync) â”€â”€â”€â”€â”€â”€â”€
ADO_ORG_URL=https://dev.azure.com/YourOrg
ADO_PROJECT=YourProject
ADO_PAT=your-personal-access-token
# Token renewal: https://dev.azure.com/YourOrg/_usersSettings/tokens
# Required scopes: Work Items (Read & Write)

ADO_WORK_ITEM_TYPE=Issue
ADO_DEFAULT_AREA_PATH=YourProject
ADO_PARENT_EPIC_TITLE=Electronics AI Working Group Opportunities
```

> **Security:** `.env` is gitignored. Never commit it. Never put secrets in any `.json` or `.py` file.

---

## Human Review Rules

Before a row is pushed to SharePoint or ADO, review:

```text
Title                     â€” accurate and specific?
ProblemPainPoint          â€” clearly describes the real pain?
EvidenceSummary           â€” grounded in what was actually said?
SourceSpeaker / Timestamp â€” traceable to the transcript?
OperatingBucket           â€” correct business area?
AIUseCaseType             â€” Classification, Action, or Both?
LevelOfAnalysis           â€” does this match what was described?
MaturitySignal            â€” honest about how mature this actually is?
GuardrailsNeeded          â€” are the right risks called out?
NextStep                  â€” actionable and realistic?
SuggestedOwners           â€” are these real people and correct teams?
ADO push                  â€” has the row been reviewed before pushing?
```

**Do not trust model output without human validation.**

---

## Operating Principles â€” Governance

- Rows created from transcripts **always** default to `Needs Review`.
- The model can extract, classify, and suggest. It cannot approve.
- `--push-ado` is **always opt-in** and always follows human review.
- The ADO sync (Step 0) is **read-only** â€” it never creates or modifies ADO items automatically.
- Power Automate push is disabled by default (`ENABLE_POWER_AUTOMATE_PUSH=false`).
- `master_opportunities.xlsx` is the Power BI source â€” close it in Excel before a rebuild.

---

## Future Enhancements

The following capabilities have been proposed but are not yet implemented:

```text
Duplicate detection against existing SharePoint items
Automatic enrichment of existing SharePoint rows
KB article candidate detection and draft creation
Solution Registry integration
Teams adaptive card approval workflow
ADO comment parsing (pull discussion context from ADO back into reports)
Power BI dataset push trigger
Owner / SME notification on new push
```

See `docs/future-features/` for detailed proposals.

---

## Success Criteria

The system succeeds when it can:

```text
âœ… Read a DOCX transcript
âœ… Extract relevant chunks without sending the full transcript to AI
âœ… Produce candidate AI opportunities with evidence
âœ… Classify opportunities into the full SharePoint schema
âœ… Generate a human-reviewable workbook
âœ… Generate a SharePoint-ready JSON payload
âœ… Optionally post draft rows to Power Automate
âœ… Archive each week and build trend reports week-over-week
âœ… Push approved opportunities to Azure DevOps as tracked Issues
âœ… Sync live ADO status back into reports automatically
âœ… Answer "where are we at?" for any prior week's discussion via the Progress tab
âœ… Preserve evidence, traceability, and human review at every step
```

---

## Important Guardrail

This agent is an intake assistant and a progress tracker â€” not a decision-maker.

It can extract, classify, suggest, push, sync, and report. It should not approve, publish, scale, or finalize AI opportunities without a human in the loop.
