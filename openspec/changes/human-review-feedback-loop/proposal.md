# Proposal: Human-Review Feedback Loop

## Why

Classified opportunities currently flow from the AI model directly to the review
workbook and ADO with no structured record of what a human accepted, corrected, or
rejected. This means:

- Every week starts from scratch — the model never learns from reviewer judgement
- Corrections exist only in Excel edits that are never captured back into the system
- Approvals and rejections cannot be audited or replicated
- Prompt/classifier quality can only be assessed by reading individual outputs, not
  by running against a defined evaluation set
- ADO items can be pushed before a reviewer has formally approved the opportunity

The result is a system that does not improve over time and cannot enforce that only
reviewed, approved opportunities reach Azure DevOps.

## What Changes

### New: Review queue

After classification, each opportunity enters a structured review queue persisted in
`output/review_queue/`. A reviewer works through the queue using a CLI or the existing
HTML report and can: **approve**, **reject**, **request re-extract**, **split** into
two items, **merge** with another, or **edit any classification field** before approval.

### New: Dual-value field preservation

Every classified row gains a `_model` sub-object (the raw model output) alongside the
working values. When a reviewer changes a field, the original model value is preserved
and the corrected value is captured with reviewer identity and timestamp.

### New: Structured feedback store

Approvals, rejections, and field corrections are written to
`output/feedback/feedback_log.jsonl` as structured records. Each record carries: the
opportunity title, date, action (approve/reject/edit), field name, original model value,
reviewer-corrected value, reviewer ID, and timestamp.

### New: Feedback-driven prompt improvement (controlled)

A `--apply-feedback` command reads the accumulated feedback log and proposes prompt
and/or few-shot example updates. Proposed updates are written to a staging area
(`config/feedback_staging/`) and must pass an evaluation run before promotion.
Promotion requires an explicit `--promote-feedback <version>` command. No self-modification
occurs without this explicit human approval.

### New: Evaluation dataset and regression suite

Accepted reviewer decisions are accumulated into `config/eval/` as labelled examples.
A `--eval` command runs the current classifier against the eval set and produces a
precision/recall/field-accuracy report. The report is written to `output/eval/` and
must pass a minimum accuracy threshold before any feedback promotion is permitted.

### New: ADO publish gate

`--push-ado` is modified to push only rows with `review_status = "approved"`. Rows
without explicit reviewer approval are blocked from ADO. The existing title-dedup
guard is retained.

### Preserved / Unchanged

- All transcript ingestion, cleaning, chunking, extraction, and classification logic
- All HTML report generation (weekly, monthly, cards, trends, progress tabs)
- All ADO status sync logic (Step 0, read-only)
- The existing `--mock`, `--mode`, `--date`, `--include-low-confidence` flags
- All history store, master exporter, and presentation builder behavior

## Capabilities

### New Capabilities

- `review-queue`: Structured persistent queue of classified rows awaiting reviewer
  action; supports approve/reject/split/merge/edit operations
- `feedback-capture`: Structured JSONL log of every reviewer decision with full
  provenance (model value, reviewer value, reviewer ID, timestamp)
- `feedback-staging`: Controlled process for converting feedback into prompt/example
  updates; staged in config, version-tagged, not applied without explicit promotion
- `evaluation-suite`: Labelled example set drawn from accepted reviewer decisions;
  `--eval` mode runs classifier against it and reports field-level accuracy

### Modified Capabilities

- `ado-work-item-sync`: `--push-ado` now gates on `review_status = "approved"` per row;
  rows without approval are skipped with a warning
- `opportunity-classification`: Each classified row gains `_model` snapshot and
  `review_status`, `reviewer_id`, `reviewer_timestamp`, `reviewer_notes` fields
- `trend-reporting`: Weekly report review queue tab shows pending/approved/rejected
  counts; approved badge appears on cards for reviewed items

## Impact

### Pipeline stages affected

| Stage | Change |
|-------|--------|
| Steps 1-4 (ingestion, extraction) | None |
| Step 5 (classification) | Row schema gains review + model-snapshot fields |
| Steps 6-8 (export, payload, report) | Review queue integration; report gains review status tab |
| Step 9c (ADO push) | Gated to approved rows only |
| Step 0 (ADO sync) | None |

### New modules

| Module | Purpose |
|--------|---------|
| `src/review_queue.py` | Queue persistence, action handlers (approve/reject/edit/split/merge/requeue) |
| `src/feedback_store.py` | JSONL append-only log; read/query API |
| `src/feedback_applier.py` | Converts feedback log into staged prompt/example updates |
| `src/evaluator.py` | Runs eval set through classifier; reports accuracy metrics |

### Modified modules

| Module | Change |
|--------|--------|
| `src/classifier.py` | Preserve model output in `_model`; add review status fields to schema |
| `src/main.py` | New CLI modes: `review`, `apply-feedback`, `eval`, `promote-feedback` |
| `src/ado_client.py` | Push gate: skip rows without `review_status = "approved"` |
| `config/mvp_output_schema.json` | 4 new review fields + `_model` snapshot field |

### New config / data files

| File | Purpose |
|------|---------|
| `output/review_queue/<date>/queue.json` | Per-week review queue state |
| `output/feedback/feedback_log.jsonl` | Append-only reviewer decision log |
| `config/feedback_staging/<version>/` | Staged prompt/example proposals |
| `config/eval/examples.jsonl` | Labelled examples for evaluation |
| `output/eval/` | Evaluation run reports |
| `.env.example` | `REVIEWER_ID` variable |

### Dependencies

- No new third-party libraries required for core review queue and feedback store
- `pytest` added as a dev dependency for the evaluation regression tests
- All new data files go to `output/` (gitignored) or `config/` (committed, version-controlled)

### Backward compatibility

All new fields are nullable. `review_status` defaults to `None` (unreviewed). The
existing pipeline runs identically — the only behavioral change is that `--push-ado`
now skips unreviewed rows with a printed warning rather than pushing everything.
