# Transcript-Intake-Agent
Python agent that extracts AI opportunities from meeting transcripts, classifies them into the AI Acceleration framework, generates reviewable SharePoint-ready rows, and optionally posts draft intake records through Power Automate with human review.
# AI Transcript Intake Agent

> 📋 **New operator?** See [`Operating Procedure/operating_manual.html`](Operating%20Procedure/operating_manual.html) for the full step-by-step manual.
> 📖 **Want the system overview?** See [`Overview/process_overview.html`](Overview/process_overview.html) for the visual flowchart.

## Purpose

This repository contains a Python-based local agent workflow for converting Electronics AI Working Group meeting transcripts into structured AI opportunity intake records.

The goal is to use meeting transcripts as a source of organizational signal, extract potential AI use cases, classify them against the Electronics AI Acceleration framework, generate reviewable outputs, and optionally send approved draft rows to a SharePoint list through a Power Automate HTTP endpoint.

This project is designed to support the Electronics AI Working Group operating model:

```text
Meeting transcript
    ↓
AI opportunity extraction
    ↓
Classification against defined dimensions
    ↓
Human review
    ↓
SharePoint intake list
    ↓
Power BI / KB / demo backlog / release candidate tracking
```

The agent should help reduce the manual effort required to convert working group discussions into structured SharePoint records while preserving human review, ownership, and governance.

> 📖 **New here?** See **[`Overview/process_overview.html`](Overview/process_overview.html)**
> for a visual flowchart of the whole process plus instructions for keeping it
> running. Open it with `./Overview/open_overview.ps1` (or `Invoke-Item "Overview/process_overview.html"`).

---

## Operating Principles

This project is intentionally designed around a few core principles:

1. **Do not send full transcripts to the model unless required.**
   Use deterministic preprocessing, keyword filtering, speaker-turn parsing, and chunking before invoking AI.

2. **AI output is draft-only.**
   Rows created from transcripts should default to `Needs Review`.

3. **Human review is required before SharePoint records are treated as official.**
   The model can extract, classify, and recommend; it should not be the final decision-maker.

4. **Classification and Action are different.**
   Classification use cases help us understand the work. Action use cases create, update, trigger, send, or change a workflow or system.

5. **Preserve evidence.**
   Extracted opportunities should include speaker, timestamp, and evidence summary when available.

6. **Optimize token usage.**
   Use scripts for deterministic text handling. Only send relevant chunks and concise prompts to the model.

7. **SharePoint writeback should be controlled.**
   The MVP creates review files and SharePoint-ready payloads. Posting to SharePoint should happen only through a controlled Power Automate HTTP endpoint.

---

## MVP Scope

The minimum viable product does the following:

```text
Input:
- DOCX meeting transcript

Outputs:
- output/transcript_chunks.json
- output/candidates.json
- output/classified_rows.json
- output/review_rows.xlsx
- output/sharepoint_payload.json

Optional:
- POST approved payload to Power Automate HTTP endpoint
```

The MVP does **not** automatically update existing SharePoint rows.
The MVP does **not** automatically create KB articles.
The MVP does **not** bypass human review.

---

## Project Structure

```text
ai-transcript-intake-agent/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── .github/
│   └── copilot-instructions.md
│
├── config/
│   ├── choice_values.json
│   ├── sharepoint_field_mapping.json
│   └── extraction_settings.json
│
├── skills/
│   ├── extract_opportunities.md
│   ├── classify_opportunity.md
│   ├── build_sharepoint_payload.md
│   └── token_optimization.md
│
├── src/
│   ├── main.py
│   ├── transcript_reader.py
│   ├── transcript_cleaner.py
│   ├── transcript_chunker.py
│   ├── candidate_detector.py
│   ├── classifier.py
│   ├── validators.py
│   ├── review_exporter.py
│   ├── report_generator.py
│   ├── power_automate_client.py
│   ├── period_utils.py          # meeting-date / week / month resolution
│   ├── opportunity_matcher.py   # deterministic week-over-week matching
│   ├── history_store.py         # cumulative opportunity history
│   ├── trend_analyzer.py        # weekly / monthly trend metrics
│   └── trend_reporter.py        # weekly + monthly HTML reports
│
├── input/
│   └── transcripts/
│
└── output/
    ├── (current-run working files: chunks, candidates, classified_rows,
    │    review_rows.xlsx, sharepoint_payload.json, ai_opportunity_report.html)
    ├── weeks/<YYYY-MM-DD>/       # per-week archive + weekly_report.html
    ├── history/opportunities.json   # cumulative cross-week history
    └── reports/monthly_<YYYY-MM>.html
```

---

## Core Workflow

### 1. Read transcript

The agent reads a `.docx` meeting transcript from:

```text
input/transcripts/
```

### 2. Clean transcript

The transcript is normalized while preserving speaker and timestamp information.

### 3. Chunk transcript

The transcript is parsed into speaker turns, filtered using candidate keywords, and packed into smaller chunks to reduce token usage.

### 4. Extract candidates

The model identifies possible AI opportunities, demos, KB candidates, access issues, governance topics, cost issues, or reusable patterns.

### 5. Classify candidates

Each candidate is mapped into the AI Acceleration SharePoint schema.

### 6. Export review workbook

The agent creates a review workbook so a human can inspect, edit, approve, or reject the extracted rows.

### 7. Build SharePoint payload

The agent creates a SharePoint-ready JSON payload using internal field mappings.

### 8. Optional Power Automate push

If enabled, the agent posts the payload to a Power Automate HTTP endpoint, which creates draft SharePoint list rows.

---

## AI Acceleration Classification Framework

Every extracted opportunity should be classified across the following dimensions.

### AI Use Case Type

```text
Classification
Action
Both Classification and Action
Unknown / Needs Review
```

### Classification

Use this when AI helps the user understand the work.

Examples:

```text
Summarize
Organize
Compare
Explain
Group
Categorize
Identify patterns
Prioritize signals
Extract themes
Analyze feedback
Analyze meeting transcripts
```

### Action

Use this when AI helps perform or change the work.

Examples:

```text
Create records
Update records
Trigger workflows
Send notifications
Generate code
Create documentation
Open work items
Update a SharePoint list
Generate release notes
Automate a workflow
```

### Default rule

Prefer `Classification` unless the transcript clearly describes creating, updating, triggering, sending, automating, or changing a system.

All `Action` and `Both Classification and Action` use cases require human review.

---

## Operating Buckets

Each opportunity should be mapped to one of the following:

```text
Outside / Pre-Sale
Inside / Pre-Sale
Manufacturing
Post Shipment
Cross-Functional / Governance
Unknown / Needs Review
```

---

## Process Stages

Use one or more of the following process stages:

```text
Opportunities
Solution Development
Solution Approval
Order Validation
Order Creation
Order Activation
Production
EOL Testing
Delivery
Installation
Deployment
Incident Identification
Claim
Investigation
Approval
Solution Implementation
Sustaining
Resolution
Feedback Loop
Governance / Intake
Unknown / Needs Review
```

---

## Levels of Analysis

```text
Level 0 — Signal Capture
Level 1 — Categorization
Level 2 — Descriptive Analysis
Level 3 — Diagnostic Analysis
Level 4 — Predictive / Risk Analysis
Level 5 — Prescriptive Recommendation
Level 6 — Action / Automation
Level 7 — Release Candidate
```

### Level definitions

```text
Level 0 — Signal Capture
A use case, idea, tool, or concern was mentioned but is not yet mature.

Level 1 — Categorization
The main value is organizing the item into the taxonomy.

Level 2 — Descriptive Analysis
AI summarizes what happened or what exists.

Level 3 — Diagnostic Analysis
AI helps explain why something is happening.

Level 4 — Predictive / Risk Analysis
AI helps identify likely future risk or impact.

Level 5 — Prescriptive Recommendation
AI recommends what should happen next.

Level 6 — Action / Automation
AI creates, updates, triggers, sends, or automates.

Level 7 — Release Candidate
The use case is mature enough to become a reusable capability, KB article, pilot, or leadership-ready release candidate.
```

---

## Signal Strength

```text
Isolated Example
Repeated Within One Team
Repeated Across Multiple Teams
Cross-Functional Pattern
Leadership Priority
Unknown / Needs Review
```

Use stronger signal ratings when multiple teams mention the same need, when leadership explicitly prioritizes the item, or when the pattern appears reusable across functions.

---

## Expected SharePoint Fields

The classifier should produce rows with these logical field names:

```json
{
  "Title": "",
  "UseCaseDescription": "",
  "ProblemPainPoint": "",
  "RequestedBy": "",
  "RequestingTeam": "",
  "CurrentStatus": "Needs Review",
  "Priority": "High",
  "OperatingBucket": "",
  "ProcessStage": "",
  "FunctionalLens": "",
  "AIUseCaseType": "",
  "PrimaryAIFunction": "",
  "LevelOfAnalysis": "",
  "SignalStrength": "",
  "PrimaryTool": "",
  "SupportingTools": [],
  "PrimaryDataSource": "Meeting Transcript",
  "SystemOfRecord": "SharePoint List",
  "IntegrationNeeded": false,
  "DataSensitivity": "Internal",
  "BusinessOwner": "",
  "TechnicalOwner": "",
  "SMEChampion": "",
  "GuardrailsNeeded": "",
  "HumanInTheLoopRequired": true,
  "NextStep": "",
  "ConfidenceLevel": "",
  "EvidenceSummary": "",
  "SourceSpeaker": "",
  "SourceTimestamp": ""
}
```

The file `config/sharepoint_field_mapping.json` maps these logical names to SharePoint internal field names.

---

## Default Row Values

Unless the transcript clearly supports something else, default to:

```text
CurrentStatus = Needs Review
Priority = High
PrimaryDataSource = Meeting Transcript
SystemOfRecord = SharePoint List
DataSensitivity = Internal
HumanInTheLoopRequired = true
ScheduleHealth = Not Started
```

---

## Example Extracted Opportunities

The system should be able to extract items like:

```text
PR Release Notes Automation
Copilot Access Standard Work
Digital Product Documentation Pipeline
Support File Triage / Diagnostic Summarization
AI Token Cost Governance & Reporting
Reusable Skills Repository / Skill Distribution Model
SharePoint KB + Bot Knowledge Source
AI Demo Intake to KB Conversion Workflow
AI SME / Champion Network Registry
AI Survey Synthesis & Enablement Roadmap
```

---

## Token Optimization Strategy

Token usage should be minimized by design.

### Do this

```text
Read DOCX locally.
Clean transcript locally.
Parse speaker turns locally.
Filter transcript using keywords locally.
Send only relevant chunks to the model.
Classify one candidate at a time.
Use concise JSON schemas.
Use local validation for allowed values.
Use deterministic scripts before AI whenever possible.
```

### Avoid this

```text
Do not send the entire transcript to the model by default.
Do not ask the model to clean formatting that Python can clean.
Do not send the full SharePoint schema repeatedly.
Do not use long chat history for repeated runs.
Do not ask the model to deduplicate when local fuzzy matching is sufficient.
Do not auto-post to SharePoint without review.
```

---

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

### 2. Activate virtual environment

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create environment file

Copy:

```bash
.env.example
```

To:

```bash
.env
```

Add the Power Automate endpoint only when ready.

```env
POWER_AUTOMATE_URL=https://replace-with-your-flow-url
ENABLE_POWER_AUTOMATE_PUSH=false
DEFAULT_STATUS=Needs Review
```

---

## How to Run

### Dry run

Use this to read and chunk a transcript.

```bash
python src/main.py --input input/transcripts/meeting.docx --mode dry-run
```

Expected output:

```text
output/transcript_chunks.json
```

### Generate payload

After `output/classified_rows.json` exists:

```bash
python src/main.py --input input/transcripts/meeting.docx --mode payload
```

Expected output:

```text
output/review_rows.xlsx
output/sharepoint_payload.json
```

### Push to Power Automate

Only use after reviewing the payload.

```bash
python src/main.py --input input/transcripts/meeting.docx --mode push
```

---

## Weekly & Monthly Trend Analysis

The agent supports recurring **weekly transcript uploads**. Each week's transcript
is processed, archived, and merged into a cumulative history so the system can look
back over previous weeks and surface trends.

### How a week is identified

The meeting date is parsed from the transcript **filename**
(e.g. `Electronics AI - Working Session - 6_3_2026.docx` → `2026-06-03`).
Supported formats include `M_D_YYYY`, `M-D-YYYY`, `YYYY-MM-DD`, and `M.D.YY`.
If no date is found, the file's last-modified date is used. You can always override
with `--date YYYY-MM-DD`.

### Run the weekly pipeline

```bash
python src/main.py --input "input/transcripts/Electronics AI - Working Session - 6_3_2026.docx" --mode weekly
```

This runs the full classify → payload pipeline, then:

```text
1. Archives the week to       output/weeks/<YYYY-MM-DD>/
                              (classified_rows.json, review_rows.xlsx,
                               sharepoint_payload.json, weekly_report.html)
2. Ingests the rows into      output/history/opportunities.json
                              (idempotent by meeting date — re-runs do not double-count)
3. Generates the weekly HTML  output/weeks/<YYYY-MM-DD>/weekly_report.html
4. Refreshes the monthly HTML output/reports/monthly_<YYYY-MM>.html
```

**Back-dated transcripts are handled automatically.** If the transcript's meeting
date is earlier than any week already in history, the pipeline detects this and
rebuilds *every* weekly and monthly report so all longitudinal views stay accurate.
No special flag is needed — just run `--mode weekly` as normal.

Add `--mock` to test without OpenAI, and `--date` to override the meeting date.

### Rebuild all reports manually

If you ever need to force a full regeneration of every weekly and monthly report
from current history (e.g. after manual history edits, or to apply a report format
change to archived weeks):

```bash
python src/main.py --mode rebuild
```

No transcript or API key is required — it reads `output/history/opportunities.json`
and the archived `classified_rows.json` files.

### Build / refresh a monthly report

```bash
# Derive the month from a transcript filename
python src/main.py --input "input/transcripts/Electronics AI - Working Session - 6_3_2026.docx" --mode monthly

# Or target a month explicitly (no transcript needed — reads from history)
python src/main.py --mode monthly --month 2026-06
```

### What the reports show

**Weekly report** (`weekly_report.html`):

The weekly report uses the **same layout and behavior as the original
`ai_opportunity_report.html`** — a KPI header plus three interactive tabs:
**📋 Opportunity Cards** (filterable), **📊 Analytics** (donut/bar charts), and
**🗂 Full Table** — rendered over that week's opportunities. It adds one extra tab:

```text
- 📈 Trends tab (longitudinal insight layered on the canonical format):
  - KPIs: opportunities this week, new this week, carried over, escalating signal, tracked all-time
  - "New this week" cards
  - "Carried over" cards with week-over-week movement (signal ↑/↓, level ↑/↓)
  - Opportunities-per-week line for recent weeks
```

The canonical layout is produced by `report_generator.build_report_html()` (the
single source of truth); the weekly report injects the Trends tab via that
function's `extra_nav` / `extra_sections` / `extra_scripts` parameters. See
`skills/weekly_report_format.md` for the format standard and how to extend it.

**Monthly report** (`monthly_<YYYY-MM>.html`):

```text
- KPIs: unique opportunities, weeks covered, new this month, carried from prior, escalating
- Opportunities per week (total / new / recurring)
- Operating-bucket distribution stacked by week
- AI use case type distribution for the month
- Signal / level momentum table (escalations)
- Full table of opportunities active this month with first-seen / last-seen and hit counts
```

### How recurring opportunities are detected

Opportunities are matched across weeks using **deterministic fuzzy matching** in
Python (normalized title equality, difflib sequence ratio, and token overlap) — no
transcripts or model calls are involved, keeping the trend layer token-free and
fully reproducible. All trend outputs operate on `classified_rows.json`, so they
run without an OpenAI key.

> Note: On Windows, if the console raises a `UnicodeEncodeError` on the `→`
> character, set `PYTHONIOENCODING=utf-8` before running (the generated HTML is
> unaffected).

### Automatic processing on upload (folder watcher)

Instead of running the weekly pipeline by hand, you can run a watcher that monitors
`input/transcripts/` and automatically processes each new transcript as it is added.

```bash
# Watch forever — processes any new/changed .docx as soon as its upload finishes
python src/watch_transcripts.py

# Other options
python src/watch_transcripts.py --once            # process current backlog, then exit
python src/watch_transcripts.py --interval 10     # poll every 10s (default 5)
python src/watch_transcripts.py --mark-processed  # baseline existing files (record without running)
python src/watch_transcripts.py --print-only      # show what would run, without running it
```

How it works:

```text
- Pure polling — no extra dependencies, works cross-platform.
- Safe for in-progress uploads: a file is processed only after its size and
  modified time stay unchanged for one full poll interval (upload finished).
- Idempotent: processed files are recorded in
  output/history/processed_files.json (keyed by name + size + mtime), so a file
  is reprocessed only if it actually changes. The weekly pipeline is itself
  idempotent by meeting date.
- Each new transcript triggers:  main.py --input <file> --mode weekly
  which archives the week, ingests it into history, and regenerates the weekly
  and monthly HTML reports.
```

Typical first-time setup (so already-processed transcripts are not re-run):

```bash
python src/watch_transcripts.py --mark-processed   # baseline what's already done
python src/watch_transcripts.py                    # then start watching
```

> The watcher invokes `--mode weekly`, which runs extraction/classification and
> therefore requires a configured `OPENAI_API_KEY` in `.env`. Add `--mock` to
> exercise the wiring without calling OpenAI. On Windows, run inside a shell where
> `PYTHONIOENCODING=utf-8` is set (the watcher passes this to the pipeline
> automatically).

### Step 1

Run the transcript chunking script.

```bash
python src/main.py --input input/transcripts/meeting.docx --mode dry-run
```

### Step 2

Ask Copilot Chat:

```text
Use skills/extract_opportunities.md and output/transcript_chunks.json.

Extract candidate AI opportunities from the transcript chunks.
Return only valid JSON.
Save the result as output/candidates.json.

Do not invent use cases.
Preserve speaker and timestamp evidence.
```

### Step 3

Ask Copilot Chat:

```text
Use skills/classify_opportunity.md and output/candidates.json.

Classify each candidate into the AI Acceleration SharePoint schema.
Return only valid JSON.
Save the result as output/classified_rows.json.

Default CurrentStatus to Needs Review unless evidence supports another status.
Default HumanInTheLoopRequired to true.
```

### Step 4

Generate the review workbook and SharePoint payload.

```bash
python src/main.py --input input/transcripts/meeting.docx --mode payload
```

### Step 5

Review:

```text
output/review_rows.xlsx
output/sharepoint_payload.json
```

### Step 6

Push only after review:

```bash
python src/main.py --input input/transcripts/meeting.docx --mode push
```

---

## Power Automate Payload

The Python agent will send payloads like this to Power Automate:

```json
{
  "source": "ai-transcript-intake-agent",
  "mode": "draft-create",
  "rowCount": 1,
  "rows": [
    {
      "fields": {
        "Title": "Digital Product Documentation Pipeline",
        "CurrentStatus": "Needs Review",
        "Priority": "High",
        "AIUseCaseType": "Both Classification and Action",
        "PrimaryDataSource": "Meeting Transcript",
        "HumanInTheLoopRequired": true,
        "EvidenceSummary": "David Hein demonstrated a product documentation pipeline using AI-supported content generation and review."
      }
    }
  ]
}
```

Power Automate should create the SharePoint item as a draft or needs-review row.

---

## Power Automate Flow Design

The recommended flow is:

```text
Trigger: When an HTTP request is received
    ↓
Parse JSON
    ↓
Apply to each rows
    ↓
Create item in SharePoint
    ↓
Respond to caller
```

The flow should not mark records as approved.
The flow should create draft records only.

---

## Human Review Rules

Before a row becomes official, review:

```text
Title
Description
Business owner
SME / Champion
AI use case type
Functional lens
Operating bucket
Process stage
Tool and data source
Guardrails
Next step
Evidence summary
```

Do not trust model output without human validation.

---

## Future Enhancements

After the MVP is stable, possible enhancements include:

```text
Duplicate detection against existing SharePoint items
Automatic enrichment of existing rows
KB article candidate detection
KB article draft creation
Solution Registry integration
Miro board update instructions
Power BI refresh trigger
Owner / SME notification
Teams adaptive card approval
```

These should not be part of the first MVP unless explicitly added.

---

## Success Criteria

The MVP is successful when it can:

```text
Read a DOCX transcript
Extract relevant transcript chunks
Produce candidate AI opportunities
Classify opportunities into the SharePoint schema
Generate a review workbook
Generate a SharePoint-ready JSON payload
Optionally post draft rows to Power Automate
Preserve evidence and human review
Reduce manual effort compared to hand-entering rows
```

---

## Important Guardrail

This agent is an intake assistant, not a decision-maker.

It can extract, classify, suggest, and prepare records.
It should not approve, publish, scale, or finalize AI opportunities without human review.
