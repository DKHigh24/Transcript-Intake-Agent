# Transcript-Intake-Agent
Python agent that extracts AI opportunities from meeting transcripts, classifies them into the AI Acceleration framework, generates reviewable SharePoint-ready rows, and optionally posts draft intake records through Power Automate with human review.
# AI Transcript Intake Agent

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
│   └── power_automate_client.py
│
├── input/
│   └── transcripts/
│
└── output/
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

## Recommended VS Code / GitHub Copilot Workflow

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
