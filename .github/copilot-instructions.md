# Copilot Instructions

This repo builds a Python-based AI Transcript Intake Agent.

The agent reads DOCX meeting transcripts from the Electronics AI Working Group, extracts AI opportunities, classifies them into the AI Acceleration SharePoint framework, creates reviewable outputs, optionally prepares/pushes draft rows through a Power Automate HTTP endpoint, and — to **close the loop on where the work actually occurs** — pushes approved opportunities to Azure DevOps as tracked Issues and syncs their live status back into every weekly report.

## Core rules

- Do not send full transcripts to the model by default.
- Use Python for deterministic work: DOCX reading, cleaning, chunking, keyword filtering, JSON validation, Excel export, payload building, HTTP posting, ADO REST calls, and ADO status sync.
- Use AI only for semantic work: opportunity extraction, classification, owner/SME inference, guardrail wording, and next-step wording.
- All model output is draft-only.
- Default SharePoint rows to `Needs Review`.
- Human review is required before any SharePoint push.
- Human review is required before any ADO push (`--push-ado` is always opt-in).
- The ADO sync (Step 0) is read-only — it never creates or modifies ADO items automatically.
- Do not commit secrets. ADO_PAT lives in `.env` only.
- Do not hard-code Power Automate URLs or ADO credentials.
- Use `config/sharepoint_field_mapping.json` for SharePoint internal names.
- Use `config/choice_values.json` for allowed choice values.
- Use `config/mvp_output_schema.json` for expected output structure (includes 7 ADO fields).
- Use `config/ado_field_mapping.json` as reference for ADO REST API field paths.

## Full pipeline flow (--mode weekly)

0. ADO status sync — read-only bulk GET for all known ADOWorkItemIds; updates ADOStatus/Iteration/AssignedTo/LastUpdated across all archived weeks (skipped if ADO_PAT absent).
1. Read DOCX transcript.
2. Clean transcript.
3. Split into speaker turns.
4. Keyword-filter and chunk relevant turns.
5. Extract candidate AI opportunities. (AI)
6. Deduplicate candidates (deterministic fuzzy match).
7. Classify candidates into the MVP schema. (AI)
8. Validate rows against choice_values.json; route low-confidence to triage.
9. Export review_rows.xlsx.
10. Build sharepoint_payload.json.
11. Generate ai_opportunity_report.html (Cards / Analytics / Table tabs).
12. Archive week to output/weeks/<YYYY-MM-DD>/.
13. Update master_opportunities.xlsx (Power BI source; includes ADO columns AS–AY, with WeekDate at AR).
14. Push to ADO (opt-in --push-ado only): create Issues under parent Epic; title dedup prevents duplicates; write back ADOWorkItemId/Url/Status/PushedAt to archive.
15. Ingest into output/history/opportunities.json.
16. Generate weekly report with 5 tabs: Cards / Analytics / Table / Trends / Progress.
17. Generate monthly rollup report.
18. Generate upcoming session presentation (PPTX).

## ADO integration specifics

- `src/ado_client.py` is the sole ADO module. Public API: `is_configured()`, `sync_all_weeks()`, `get_or_create_epic()`, `push_work_item(row, epic_id)`.
- ADO state vocabulary is Basic process: `To Do`, `Doing`, `Done`. Handle Agile (`New`, `Active`, `Resolved`) as fallback.
- The Progress tab in weekly reports groups all historical ADO-linked rows by current state, highlights items moved in the last 7 days, and answers "where are we at with X we discussed?"
- ADO chips on opportunity cards show colored state badges + direct links when ADOWorkItemId is present.
- All ADO fields in classified_rows.json and master_opportunities.xlsx remain null until --push-ado is run.
