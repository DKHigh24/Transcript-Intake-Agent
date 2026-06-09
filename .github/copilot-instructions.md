# Copilot Instructions

This repo builds a Python-based AI Transcript Intake Agent.

The agent reads DOCX meeting transcripts from the Electronics AI Working Group, extracts AI opportunities, classifies them into the AI Acceleration SharePoint framework, creates reviewable outputs, and optionally prepares/pushes draft rows through a Power Automate HTTP endpoint.

Core rules:
- Do not send full transcripts to the model by default.
- Use Python for deterministic work: DOCX reading, cleaning, chunking, keyword filtering, JSON validation, Excel export, payload building, and HTTP posting.
- Use AI only for semantic work: opportunity extraction, classification, owner/SME inference, guardrail wording, and next-step wording.
- All model output is draft-only.
- Default SharePoint rows to Needs Review.
- Human review is required before any SharePoint push.
- Do not commit secrets.
- Do not hard-code Power Automate URLs.
- Use config/sharepoint_field_mapping.json for SharePoint internal names.
- Use config/choice_values.json for allowed choice values.
- Use config/mvp_output_schema.json for expected output structure.

MVP flow:
1. Read DOCX transcript.
2. Clean transcript.
3. Split into speaker turns.
4. Keyword-filter relevant transcript chunks.
5. Extract candidate AI opportunities.
6. Classify candidates into the MVP schema.
7. Export review_rows.xlsx.
8. Build sharepoint_payload.json.
9. Optionally POST to Power Automate only when explicitly enabled.
