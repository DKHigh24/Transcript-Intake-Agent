## Why

Transcripts contain two fundamentally different types of AI opportunity: ideas people are
*proposing* for the future, and tools or workflows that are *already working today*. Currently
the pipeline treats both identically — a live Copilot deployment and a whiteboard wish-list
item land in the same `(2) Needs Review` bucket. Separating these signals lets the team
track real delivery progress, celebrate working wins in presentations, and give stakeholders
an honest "aspirational vs. delivered" split in Power BI.

## What Changes

- Add `MaturitySignal` choice field to `config/choice_values.json` with four values:
  `Aspirational`, `In Progress / Piloting`, `Delivered / Active Today`, `Unknown`
- Add `MaturitySignal` to `config/mvp_output_schema.json` and `config/sharepoint_field_mapping.json`
- Update `skills/classify_opportunities.md` to instruct the model to infer `MaturitySignal`
  from the verbatim evidence phrase (linguistic marker detection)
- Update `skills/extract_opportunities.md` to flag maturity signal language during extraction
- Surface `MaturitySignal` as a colored badge on HTML opportunity cards (`src/report_generator.py`)
- Add `MaturitySignal` column to `output/master_opportunities.xlsx` (`src/master_exporter.py`
  and `src/review_exporter.py`)
- Highlight "Delivered / Active Today" rows distinctly in the PPTX deck (`src/presentation_builder.py`)

## Capabilities

### New Capabilities

- `maturity-signal-detection`: Classify each extracted opportunity as Aspirational, In Progress,
  Delivered, or Unknown based on linguistic patterns in the speaker's evidence (e.g., "we should
  explore" vs. "we're already using" vs. "this is live in production")

### Modified Capabilities

- `opportunity-classification`: Add `MaturitySignal` to the classification schema and classifier
  prompt rules; update output validation
- `opportunity-extraction`: Instruct extractor to capture maturity-signal phrases in evidence
- `trend-reporting`: Surface `MaturitySignal` as a badge on cards in weekly/monthly HTML reports
- `meeting-presentation`: Distinguish "Delivered / Active Today" opportunities as a dedicated
  slide section ("Live Wins This Week")

## Impact

- **Pipeline stages affected**: opportunity-extraction (2), opportunity-classification (3),
  trend-reporting (4), meeting-presentation (5)
- **Config files**: `config/choice_values.json`, `config/mvp_output_schema.json`,
  `config/sharepoint_field_mapping.json`
- **Skills**: `skills/classify_opportunities.md`, `skills/extract_opportunities.md`
- **Source**: `src/report_generator.py`, `src/review_exporter.py`, `src/master_exporter.py`,
  `src/presentation_builder.py`
- **No breaking changes** — `MaturitySignal` defaults to `"Unknown"` for all existing rows;
  no existing field is modified or removed
- **Existing history**: Re-running all transcripts will back-fill `MaturitySignal` via the
  classifier; existing archived rows without it will show `""` / `"Unknown"` in reports
