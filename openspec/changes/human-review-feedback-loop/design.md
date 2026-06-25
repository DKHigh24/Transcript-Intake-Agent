# Design: Human-Review Feedback Loop

## 1. Current State Assessment

### Pipeline flow (current)
```
DOCX -> clean -> chunk -> keyword-filter -> extract (AI) -> dedup -> classify (AI)
     -> validate -> export review_rows.xlsx -> build payload -> archive
     -> ADO push (--push-ado) -> ingest history -> generate reports
```

The two AI steps (extract + classify) emit JSON. Everything else is deterministic Python.

After classification, a human opens `review_rows.xlsx`, makes corrections in Excel,
and the system never sees those corrections. Any corrected rows that are pushed to ADO
carry the *original* model values, not the reviewer's.

### Artifacts in play

| Artifact | Purpose |
|----------|---------|
| `output/classified_rows.json` | Current-run classified rows (working copy) |
| `output/weeks/<date>/classified_rows.json` | Archived per-week rows (authoritative) |
| `output/review_rows.xlsx` | Excel review workbook (human edits are lost) |
| `output/history/opportunities.json` | Cumulative history (ingested from classified_rows) |
| `config/mvp_output_schema.json` | Canonical field list |

### Key constraints to preserve
- No uncontrolled self-modification of the classifier
- No AI calls in deterministic pipeline steps
- ADO push is always opt-in via `--push-ado`
- Missing ADO PAT silently skips push/sync

---

## 2. Proposed Architecture

```
DOCX -> [Steps 1-5] -> classified_rows.json
                              |
                    +---------v----------+
                    |  REVIEW QUEUE      |
                    |  (new Step 5a)     |
                    |  queue.json persists
                    |  reviewer actions  |
                    +---------+---------+
                              |
              +---------------+---------------+
              |               |               |
           approved        rejected        pending
              |               |
              v               v
        push to ADO      feedback_log.jsonl
        history ingest   (reviewer correction)
        HTML reports
```

### Module responsibilities

```
src/
  review_queue.py     -- CRUD for queue.json; action handlers; no AI
  feedback_store.py   -- Append-only JSONL log; read/filter API; no AI
  feedback_applier.py -- Converts feedback into staged prompt updates; no AI
  evaluator.py        -- Runs eval examples through current classifier (AI OK here)
```

### Data flow for feedback improvement (controlled)

```
feedback_log.jsonl
       |
       | --apply-feedback
       v
config/feedback_staging/<version>/
  proposed_examples.jsonl     -- few-shot examples from corrections
  proposed_rules.md           -- rule delta from patterns
  version.yaml                -- version tag, threshold, change summary

       |
       | --eval (run classifier against config/eval/examples.jsonl)
       v
output/eval/eval_<version>.json
  field_accuracy per field
  precision / recall
  pass / fail against threshold

       |
       | --promote-feedback <version> (only if eval passes)
       v
skills/classify_opportunities.md   -- rules section updated
src/classifier.py                  -- few-shot block injected
config/eval/examples.jsonl         -- new examples appended
```

---

## 3. Review Workflow

### States

```
None (unreviewed) -> pending -> approved
                             -> rejected
                             -> needs_reprocess (returned for re-extraction)
```

### Actions

| Action | Description |
|--------|-------------|
| `approve` | Confirm row as-is; mark `review_status = approved` |
| `reject` | Discard row; mark `review_status = rejected`; log reason |
| `edit` | Change one or more fields; preserve model values in `_model`; then approve |
| `split` | Create two rows from one; both enter queue as new unreviewed items |
| `merge` | Combine two rows into one; reviewer edits merged row; mark source as merged |
| `requeue` | Return row with note; mark `review_status = needs_reprocess` |

### CLI invocation

```
# Show review queue for current run
python src/main.py --mode review

# Or for a specific archived week
python src/main.py --mode review --date 2026-06-17

# Interactive prompt: [A]pprove / [R]eject / [E]dit / [S]plit / [M]erge / [Q]ueue
```

### Reviewer identity

Set `REVIEWER_ID` in `.env`. Defaults to `os.getlogin()` as fallback. The value is
written to every feedback log record.

---

## 4. Data Model Changes

### New review fields added to every classified row

```json
{
  "review_status": null,
  "reviewer_id": null,
  "reviewer_timestamp": null,
  "reviewer_notes": null,
  "_model": {
    "Title": "<original model value>",
    "AIUseCaseType": "<original model value>",
    ...all classification fields...
  }
}
```

- `review_status`: `null | "approved" | "rejected" | "needs_reprocess" | "merged"`
- `reviewer_id`: string — from `REVIEWER_ID` env var or `os.getlogin()`
- `reviewer_timestamp`: ISO datetime string
- `reviewer_notes`: free-text string for rejection reason or edit rationale
- `_model`: snapshot of all 44 fields as they came out of the classifier
  (written once at classification time, never modified thereafter)

### Review queue state file: `output/review_queue/<date>/queue.json`

```json
{
  "date": "2026-06-17",
  "created_at": "2026-06-25T10:00:00",
  "items": [
    {
      "id": "slug-of-title",
      "status": "approved",
      "action_history": [
        {
          "action": "edit",
          "field": "AIUseCaseType",
          "from": "Classification",
          "to": "Automation",
          "reviewer_id": "dk.high",
          "timestamp": "2026-06-25T10:05:00"
        },
        {
          "action": "approve",
          "reviewer_id": "dk.high",
          "timestamp": "2026-06-25T10:05:30"
        }
      ]
    }
  ]
}
```

### Feedback log record: `output/feedback/feedback_log.jsonl`

```json
{
  "event": "field_edit",
  "opportunity_id": "slug-of-title",
  "date": "2026-06-17",
  "field": "AIUseCaseType",
  "model_value": "Classification",
  "reviewer_value": "Automation",
  "reviewer_id": "dk.high",
  "timestamp": "2026-06-25T10:05:00",
  "reviewer_notes": "This clearly creates/triggers an action"
}
```

---

## 5. Schema Versioning

### Approach: version tag in config

`config/mvp_output_schema.json` gains a `schema_version` field at the top level.
Current: `1`. This change: `2`.

When loading archived `classified_rows.json` files, `review_queue.py` reads the schema
version from the row (or defaults to 1 if absent) and applies a migration function to
add missing review fields with null defaults. Migration functions are pure Python in
`src/schema_migrations.py` — one function per version transition.

```python
MIGRATIONS = {
    1: migrate_v1_to_v2,   # add review fields + _model snapshot
}
```

Migrations are non-destructive: they only add fields, never remove or rename.

---

## 6. Feedback Storage and Retrieval

### Storage: append-only JSONL

`output/feedback/feedback_log.jsonl` — one JSON record per line.

- Written by `feedback_store.append(record)` — no reads, no locking issues
- Never modified after write
- Gitignored (contains reviewer names and timestamps, not source code)

### Retrieval API: `feedback_store.py`

```python
def load_all() -> list[dict]: ...
def filter_by_field(field: str) -> list[dict]: ...
def filter_by_action(action: str) -> list[dict]: ...
def get_edit_pairs(field: str) -> list[tuple[str, str]]: ...
```

### Feedback -> examples pipeline

`feedback_applier.py`:

1. Read all `field_edit` records from feedback log
2. For each edited field, find the corresponding transcript chunk from the archive
3. Build a few-shot example: `{"field": X, "model_value": Y, "reviewer_value": Z, "evidence": <chunk>}`
4. Write to `config/feedback_staging/<version>/proposed_examples.jsonl`
5. Analyse patterns to draft rule additions for `config/feedback_staging/<version>/proposed_rules.md`
6. Write `config/feedback_staging/<version>/version.yaml` with summary

---

## 7. Evaluation and Regression Testing

### Eval dataset: `config/eval/examples.jsonl`

Each line is a labelled example:

```json
{
  "evidence": "<transcript chunk>",
  "expected": {
    "AIUseCaseType": "Automation",
    "ConfidenceLevel": "High",
    ...
  },
  "source": "reviewer",
  "date_added": "2026-06-25"
}
```

Populated by `--apply-feedback` when promotion is initiated.

### Eval run: `--mode eval`

1. Loads `config/eval/examples.jsonl`
2. For each example, calls the current classifier (real AI call)
3. Compares model output against expected values field by field
4. Reports: per-field accuracy, overall pass rate, regression vs prior eval
5. Writes report to `output/eval/eval_<timestamp>.json`

### Promotion gate

`--promote-feedback <version>` checks the most recent eval report. If overall accuracy
is below threshold (default: 80%), promotion is blocked with instructions. Threshold
is configurable via `FEEDBACK_PROMOTION_THRESHOLD` in `.env`.

---

## 8. ADO Publishing Safeguards

### Current behavior

`--push-ado` pushes all primary rows without `ADOWorkItemId`.

### Modified behavior

`--push-ado` pushes only rows where `review_status = "approved"`.

Rows with `review_status = null` (unreviewed) are skipped with:
```
[ado] Skipping "Title" — not yet approved by reviewer (review_status=None)
```

Rows with `review_status = "rejected"` are skipped with:
```
[ado] Skipping "Title" — rejected by reviewer
```

### Bypass option

`--push-ado --skip-review-gate` bypasses the review gate (for backward compatibility
and for runs where the team decides review is not required). Emits a prominent warning:
```
[ado] WARNING: --skip-review-gate is set — pushing unreviewed opportunities
```

---

## 9. Security and Reviewer Authorization

### Reviewer identity

- `REVIEWER_ID` from `.env` — no authentication enforced (single-user local tool)
- All feedback records include reviewer ID for traceability
- No API or HTTP endpoint — all review actions happen through CLI

### Secrets

- No new secrets required beyond existing `ADO_PAT`
- Feedback log and eval examples are written to `output/` (gitignored) and `config/eval/`
  (committed as test data, no PII or secrets)
- Proposed examples in `config/feedback_staging/` are committed with version-controlled
  proposed changes and reviewed by a human before promotion

### Auditability

- `output/feedback/feedback_log.jsonl` is an immutable append-only log
- `output/review_queue/<date>/queue.json` preserves full `action_history` per item
- Both files are readable as plain JSON — no database dependency

---

## 10. Implementation Phases

### Phase 1: Review queue and data model (no AI changes)

- Add review fields to `mvp_output_schema.json`
- Write `review_queue.py` with queue persistence and action handlers
- Write `schema_migrations.py` with v1->v2 migration
- Wire `--mode review` into `main.py`
- Gate `--push-ado` on `review_status = "approved"`
- Update `review_exporter.py` to show review status column

### Phase 2: Feedback capture

- Write `feedback_store.py`
- Hook feedback append into all review actions
- Add feedback log viewer to `--mode review`

### Phase 3: Feedback staging and evaluation

- Write `feedback_applier.py`
- Write `evaluator.py`
- Wire `--mode apply-feedback` and `--mode eval` and `--mode promote-feedback`
- Build `config/eval/examples.jsonl` with initial examples

### Phase 4: Report integration

- Add review status badges to opportunity cards in HTML reports
- Add pending/approved/rejected counts to weekly report

---

## 11. File-Level Task Breakdown

See `tasks.md`.

---

## 12. Risks and Dependencies

| Risk | Mitigation |
|------|-----------|
| Reviewer corrects to an invalid choice value | `review_queue.py` validates edits against `choice_values.json` before accepting |
| `--skip-review-gate` used habitually | Warning is prominent; team governance, not technical lock |
| Archived weeks lack review fields | Schema migration on load fills nulls — backward compatible |
| Eval set too small to be meaningful | Minimum 5 examples required before `--promote-feedback` is accepted |
| Promotion applied to wrong branch | Staging dir is version-tagged; promotion is a separate explicit command |
| Feedback log grows large | JSONL is fast even at tens of thousands of lines; no practical limit for this use case |

---

## 13. Acceptance Criteria

### Review queue
- After `--mode weekly` completes, a `queue.json` exists in `output/review_queue/<date>/`
- `--mode review` renders a CLI prompt for each unreviewed item
- Approve action sets `review_status = "approved"` in the archived `classified_rows.json`
- Reject action sets `review_status = "rejected"` and logs reason
- Edit action validates against `choice_values.json` and preserves `_model` values

### ADO gate
- With `--push-ado` and no approvals, zero items are pushed and a warning is printed
- With `--push-ado` and some approvals, only approved items are pushed
- With `--push-ado --skip-review-gate`, all primary rows without `ADOWorkItemId` are pushed (legacy behavior)

### Feedback capture
- Every approve/reject/edit is written to `feedback_log.jsonl`
- Records include reviewer_id, timestamp, model_value, reviewer_value

### Schema migration
- An archived `classified_rows.json` from before this change loads without error
- Missing review fields are filled with null defaults

### Evaluation
- `--mode eval` runs without error when `config/eval/examples.jsonl` has >= 5 entries
- `--mode promote-feedback` is blocked when eval accuracy is below threshold
- After passing eval, `--mode promote-feedback` writes updated examples and rules to
  canonical config locations

### No regression
- `--mode weekly` without `--push-ado` behaves identically to pre-change
- `--mode weekly --push-ado --skip-review-gate` behaves identically to current `--push-ado`
- All existing archived weeks load and render without error after schema migration
