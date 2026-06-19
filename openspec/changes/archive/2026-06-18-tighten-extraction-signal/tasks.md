## 1. Update Extraction Prompt (skills/)

- [x] 1.1 Update `skills/extract_opportunities.md` to add a numbered substantiveness rubric — candidates must have (a) an actor, (b) a specific AI tool/domain, and (c) active delivery, active piloting, or a concrete proposal with an implied next step
- [x] 1.2 Add an explicit exclusion list to the same prompt: off-hand mentions, open-ended questions, purely aspirational statements with no specificity, and restatements already captured in the same chunk
- [x] 1.3 Add a per-chunk cap instruction to the extraction prompt: emit a maximum of 3 candidates per chunk, selecting those with the strongest evidence

## 2. Add Within-Session Deduplication (src/)

- [x] 2.1 Create `src/candidate_deduplicator.py` with a `deduplicate_candidates(candidates, threshold)` function that uses `difflib.SequenceMatcher` on combined title + evidence text to detect near-duplicates; retain the candidate with the longer EvidenceSummary; log discards at DEBUG level
- [x] 2.2 Add `DEDUP_SIMILARITY_THRESHOLD` (default 0.72) loading from `.env` in `src/main.py`
- [x] 2.3 Wire Step 4b in `src/main.py`: call `deduplicate_candidates()` immediately after extraction and before classification; log pre/post counts

## 3. Add Session Candidate Count Guardrail (src/)

- [x] 3.1 Add `MAX_CANDIDATES_PER_SESSION` (default 20) loading from `.env` in `src/main.py`
- [x] 3.2 After deduplication, if candidate count exceeds `MAX_CANDIDATES_PER_SESSION`, emit a `[warning]` log line and tag excess candidates with `_triage_reason: "exceeds_session_cap"` for downstream routing

## 4. Add Confidence Floor Filter and Triage Sheet (src/)

- [x] 4.1 In `src/main.py` (Step 5c), after classification, split rows into `primary_rows` (ConfidenceLevel != "Low") and `triage_rows` (ConfidenceLevel == "Low" or tagged with `_triage_reason`); respect `--include-low-confidence` flag which merges them back
- [x] 4.2 Update `src/review_exporter.py` to write `primary_rows` to the main "Opportunities" sheet and `triage_rows` to a second "Triage" sheet with the same column layout
- [x] 4.3 Update `src/master_exporter.py` to only append `primary_rows` (exclude triage rows) unless `include_low_confidence=True` is passed
- [x] 4.4 Add `--include-low-confidence` flag to `src/main.py` CLI argument parser

## 5. Update HTML Report (src/report_generator.py & trend_reporter.py)

- [x] 5.1 Add suppressed candidate count to the weekly HTML report summary header: "X opportunities identified, N suppressed (low confidence)" — omit N when 0
- [x] 5.2 Add a collapsible "Triage / Low Confidence (N)" section at the bottom of the weekly HTML report showing simplified triage card rows (title + evidence only); omit section entirely when N = 0

## 6. Update Config (`.env.example`)

- [x] 6.1 Add `DEDUP_SIMILARITY_THRESHOLD=0.72` and `MAX_CANDIDATES_PER_SESSION=20` to `.env.example` with comments explaining each

## 7. Verify

- [x] 7.1 Run one transcript and confirm candidate count is in the 10–20 range; check dedup log output for merged pairs
- [x] 7.2 Confirm `review_rows.xlsx` has two sheets: "Opportunities" (primary) and "Triage" (low confidence / excess)
- [x] 7.3 Confirm `master_opportunities.xlsx` excludes triage rows by default
- [x] 7.4 Open `output/weeks/<date>/weekly_report.html` and verify suppressed count in header and collapsed Triage section
- [x] 7.5 Re-run all 6 historical transcripts with `--mode rebuild` to update archives with new extraction behavior
