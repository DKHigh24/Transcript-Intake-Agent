## Why

The LLM extractor currently operates in high-recall mode — it captures every mention that could be an AI opportunity, with no minimum substantiveness threshold and no within-session deduplication. This causes a single 1-hour meeting to produce 40–44 candidate rows where 10–15 would be accurate. The result is an inflated master XLSX, cluttered opportunity cards, and diminished trust in the outputs when stakeholders review them.

## What Changes

- **Extraction prompt tightened**: Candidates must meet a minimum bar — a speaker must be proposing, piloting, or confirming a *specific* AI use case with enough detail to act on. Off-hand mentions, questions, and vague aspirations ("we should think about AI for X") are excluded unless supported by additional context.
- **Within-session deduplication**: After extraction, a deterministic Python step compares candidate titles + evidence summaries for semantic overlap within the same session. Near-duplicates (same idea surfaced from different chunks) are merged into the strongest candidate and discarded otherwise.
- **Confidence floor filter**: Candidates classified at `ConfidenceLevel = "Low"` are logged for traceability but excluded from the review workbook, HTML report cards, and master XLSX by default. A `--include-low-confidence` CLI flag re-enables them.
- **Extraction count guardrail**: If a single session produces more than a configurable `MAX_CANDIDATES_PER_SESSION` (default: 20), the pipeline emits a warning and surfaces the excess candidates in a separate triage section of the review workbook rather than the main table.

## Capabilities

### New Capabilities
- `extraction-deduplication`: Within-session candidate deduplication using title + evidence fuzzy matching before classification

### Modified Capabilities
- `opportunity-extraction`: Extraction prompt gains a substantiveness requirement and explicit exclusion rules for off-hand mentions
- `opportunity-classification`: Classification step passes `ConfidenceLevel` back to the pipeline for downstream filtering
- `trend-reporting`: Weekly HTML report gains a "Triage / Low Confidence" collapsible section for excluded candidates

## Impact

- **`src/candidate_detector.py`** — updated extraction prompt; new `MAX_CANDIDATES_PER_SESSION` guard
- **`src/classifier.py`** — `ConfidenceLevel` already classified; pipeline filter added post-classification
- **`src/main.py`** — new deduplication step (Step 4b) and confidence floor filter (Step 5c); `--include-low-confidence` flag
- **`src/trend_reporter.py` / `src/report_generator.py`** — triage section in weekly HTML
- **`src/review_exporter.py`** — low-confidence rows moved to a second sheet ("Triage") rather than main sheet
- **`src/master_exporter.py`** — low-confidence rows excluded by default
- **`skills/extract_opportunities.md`** — updated extraction prompt with substantiveness rules
- **Config**: new `MAX_CANDIDATES_PER_SESSION` key in `.env.example` and loaded in `main.py`
