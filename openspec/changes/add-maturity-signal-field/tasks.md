## 1. Update Config Files

- [x] 1.1 Add `MaturitySignal` to `config/choice_values.json` with values: `Aspirational`, `In Progress / Piloting`, `Delivered / Active Today`, `Unknown`
- [x] 1.2 Add `"MaturitySignal": ""` to `config/mvp_output_schema.json` positioned after `ConfidenceLevel`
- [x] 1.3 Add `"MaturitySignal": "MaturitySignal"` to `config/sharepoint_field_mapping.json`

## 2. Update Skills (LLM Prompts)

- [x] 2.1 Update `skills/classify_opportunities.md` with `MaturitySignal` inference rules: instruct the model to select from the four values using the linguistic marker vocabulary (Aspirational / In Progress / Delivered / Unknown signal phrases)
- [x] 2.2 Update `skills/extract_opportunities.md` to instruct the extractor to preserve verbatim maturity-signal language in `EvidenceSummary` (delivery confirmations, piloting phrases, aspirational proposals)

## 3. Update HTML Report Cards

- [x] 3.1 Add `maturity_signal` variable read from classified row in `src/report_generator.py`
- [x] 3.2 Add `MaturitySignal` colored badge to card header (green=Delivered, blue=In Progress, amber=Aspirational, gray=Unknown) in `src/report_generator.py`

## 4. Update XLSX Outputs

- [x] 4.1 Insert `MaturitySignal` after `ConfidenceLevel` (column G) in `REVIEW_COLUMNS` in `src/review_exporter.py`
- [x] 4.2 Insert `MaturitySignal` after `ConfidenceLevel` (column G) in `MASTER_COLUMNS` in `src/master_exporter.py`

## 5. Update PPTX Presentation

- [x] 5.1 Add "Live Wins This Week" slide section to `src/presentation_builder.py` that lists rows where `MaturitySignal == "Delivered / Active Today"`, inserted before the full opportunity list; omit the slide entirely when no delivered rows exist
- [x] 5.2 Include `MaturitySignal` value in speaker notes for each opportunity slide

## 6. Verify

- [x] 6.1 Run pipeline on one transcript (`--mode weekly`) and confirm `MaturitySignal` is populated on all classified rows with a valid value
- [x] 6.2 Open `output/ai_opportunity_report.html` and confirm MaturitySignal badges are visible and correctly color-coded on cards
- [x] 6.3 Open `output/master_opportunities.xlsx` and confirm `MaturitySignal` is column G adjacent to `ConfidenceLevel`
- [x] 6.4 Re-run all 6 transcripts to back-fill `MaturitySignal` and rebuild master XLSX and all reports
