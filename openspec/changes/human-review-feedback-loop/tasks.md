## Phase 1: Review Queue and Data Model

### 1.1 Schema changes

- [x] Add 4 review fields to `config/mvp_output_schema.json`:
  `review_status` (null), `reviewer_id` (null), `reviewer_timestamp` (null), `reviewer_notes` (null)
- [x] Add `_model` snapshot field to `config/mvp_output_schema.json` (object, null)
- [x] Bump `schema_version` from 1 to 2 in `config/mvp_output_schema.json`
- [x] Add `ReviewStatus` choice list to `config/choice_values.json`:
  `["approved", "rejected", "needs_reprocess", "merged"]`
- [x] Add `REVIEWER_ID` to `.env.example` with comment

### 1.2 Schema migration module

- [x] Create `src/schema_migrations.py`:
  - `CURRENT_VERSION = 2`
  - `migrate(row: dict) -> dict` — applies all needed migrations in order
  - `_migrate_v1_to_v2(row)` — adds null review fields + empty `_model` if missing

### 1.3 Classifier snapshot

- [x] In `src/classifier.py`, after parsing JSON from the LLM:
  - Deep-copy all classification field values into `row["_model"]`
  - Set `row["review_status"] = None`
  - Set `row["reviewer_id"] = None`, `row["reviewer_timestamp"] = None`, `row["reviewer_notes"] = None`

### 1.4 Review queue module

- [x] Create `src/review_queue.py`:
  - `queue_path(date: str) -> Path` — returns `output/review_queue/<date>/queue.json`
  - `load_queue(date: str) -> list[dict]` — loads or returns empty list
  - `save_queue(date: str, items: list[dict]) -> None`
  - `build_queue_from_rows(rows: list[dict], date: str) -> list[dict]` — creates queue items from classified rows
  - `action_approve(item: dict, reviewer_id: str) -> dict` — sets review_status, appends action_history
  - `action_reject(item: dict, reviewer_id: str, reason: str) -> dict`
  - `action_edit(item: dict, reviewer_id: str, field: str, new_value: str, notes: str) -> dict` — validates against choice_values.json
  - `action_requeue(item: dict, reviewer_id: str, notes: str) -> dict`
  - `apply_queue_to_rows(rows: list[dict], queue: list[dict]) -> list[dict]` — writes review fields back to rows

### 1.5 main.py: queue wiring in weekly run

- [ ] After Step 5 (classify+validate) in `run_weekly()`:
  - Build queue from `primary_rows` via `review_queue.build_queue_from_rows()`
  - Write queue to `output/review_queue/<date>/queue.json`
  - Print: `[review] Queue of N items written to output/review_queue/<date>/queue.json`
  - Print: `[review] Run --mode review --date <date> to review before ADO push`

### 1.6 ADO push gate

- [ ] In Step 9c of `run_weekly()`, add approval gate:
  - If `--skip-review-gate` is NOT set: filter `primary_rows` to only `review_status == "approved"`
  - If none pass the filter, print warning and skip the entire push block
  - If `--skip-review-gate` IS set, print prominent warning and push all (legacy behavior)
- [ ] Add `--skip-review-gate` boolean flag to argparser

### 1.7 Review mode CLI

- [x] Add `"review"` to `MODES` list in `main.py`
- [x] Create `run_review(date: str | None)` function in `main.py`:
  - Load queue from `output/review_queue/<date>/queue.json`
  - Load corresponding `classified_rows.json` from archive
  - For each pending item: display title, evidence summary, classification fields
  - Prompt: `[A]pprove / [R]eject / [E]dit / [K]skip / [Q]uit`
  - On each action: call `review_queue.action_*()`, save queue, write rows back to archive
  - Print summary at end: N approved, N rejected, N pending

### 1.8 review_exporter.py: review status column

- [x] Add `review_status` column to `REVIEW_COLUMNS` list in `src/review_exporter.py`
  (between `SignalScore` and `_validation_warnings`)
- [x] Add conditional cell fill: green for approved, red for rejected, yellow for pending

---

## Phase 2: Feedback Capture

### 2.1 Feedback store module

- [x] Create `src/feedback_store.py`:
  - `FEEDBACK_LOG_PATH = Path("output/feedback/feedback_log.jsonl")`
  - `append(record: dict) -> None` — appends one JSON line; creates file/dirs if needed
  - `load_all() -> list[dict]` — reads all records
  - `filter_by_action(action: str) -> list[dict]`
  - `filter_by_field(field: str) -> list[dict]`
  - `get_edit_pairs(field: str) -> list[tuple[str, str]]` — returns (model_value, reviewer_value) pairs

### 2.2 Hook feedback into review actions

- [x] In `review_queue.py`, after each action:
  - Build feedback record with all required fields (event, opportunity_id, date, field if edit,
    model_value, reviewer_value, reviewer_id, timestamp, notes)
  - Call `feedback_store.append(record)`

### 2.3 Feedback summary in review mode

- [x] At end of `run_review()`, print:
  - Total feedback records written this session
  - Count by action type

---

## Phase 3: Feedback Staging and Evaluation

### 3.1 Feedback applier module

- [x] Create `src/feedback_applier.py`:
  - `build_staged_version(version: str) -> Path` — creates `config/feedback_staging/<version>/`
  - `extract_examples_from_feedback(records: list[dict]) -> list[dict]` — pairs edited fields with evidence
  - `draft_rule_delta(records: list[dict]) -> str` — returns markdown text of pattern-based rule suggestions
  - `write_staging(version: str, examples: list, rule_delta: str) -> None` — writes all staging files

### 3.2 Wire apply-feedback mode

- [x] Add `"apply-feedback"` to `MODES`
- [x] Create `run_apply_feedback(version: str | None)` in `main.py`:
  - Load feedback log
  - Auto-generate version tag if not provided (e.g., `v<YYYYMMDD>`)
  - Call `feedback_applier.build_staged_version()`
  - Print: location of staged files, instructions for reviewing before promotion

### 3.3 Evaluator module

- [x] Create `src/evaluator.py`:
  - `EVAL_EXAMPLES_PATH = Path("config/eval/examples.jsonl")`
  - `load_examples() -> list[dict]`
  - `run_eval(examples: list[dict]) -> dict` — calls classifier for each example, computes field accuracy
  - `write_eval_report(results: dict, version: str) -> Path` — writes to `output/eval/`
  - `passes_threshold(results: dict, threshold: float) -> bool`

### 3.4 Wire eval mode

- [x] Add `"eval"` to `MODES`
- [x] Create `run_eval()` in `main.py`:
  - Load examples
  - Run evaluator
  - Write report
  - Print pass/fail with field-level accuracy table

### 3.5 Promotion mode

- [x] Add `"promote-feedback"` to `MODES`
- [x] Add `--feedback-version` argument to argparser
- [x] Create `run_promote_feedback(version: str)` in `main.py`:
  - Check that eval report exists and passes threshold
  - Copy proposed_examples.jsonl entries into `config/eval/examples.jsonl`
  - Apply proposed_rules.md delta to `skills/classify_opportunities.md`
  - Print confirmation with version, counts, and reminder to commit the changes
  - Write `config/feedback_staging/<version>/promoted.yaml` as a record

---

## Phase 4: Report Integration

### 4.1 HTML cards: review status badge

- [x] In `src/report_generator.py`, `_build_cards_html()`:
  - Add review status badge alongside ADO chip: green "Approved" / red "Rejected" / gray "Pending"
  - Only show badge if `review_status` is not null

### 4.2 Weekly report: review queue summary

- [x] In `src/trend_reporter.py`, `generate_weekly_report()`:
  - Compute counts: approved, rejected, pending, total
  - Inject review summary stat bar below the card grid header

---

## Verification

- [x] Run `--mode weekly` on a test transcript -- confirm queue.json is written
- [ ] Run `--mode review` -- confirm interactive CLI shows items and saves actions
- [x] Run `--mode weekly --push-ado` with no approvals -- confirm zero items pushed, warning shown
- [ ] Run `--mode weekly --push-ado` with some approved -- confirm only approved items pushed
- [x] Run `--mode weekly --push-ado --skip-review-gate` -- confirm all primary rows pushed with warning
- [ ] Check archived `classified_rows.json` -- confirm review fields written back after review
- [ ] Check `feedback_log.jsonl` -- confirm records written for each reviewer action
- [x] Load an old archived `classified_rows.json` (pre-migration) -- confirm no error, null review fields added
- [ ] Run `--mode apply-feedback` -- confirm staging dir created with examples and rule delta
- [ ] Run `--mode eval` with >= 5 examples in `config/eval/examples.jsonl` -- confirm report written
- [ ] Run `--mode promote-feedback --feedback-version <v>` when eval fails -- confirm blocked
- [ ] Run `--mode promote-feedback --feedback-version <v>` when eval passes -- confirm promotion
- [ ] Open weekly HTML report -- confirm review status badges on cards
