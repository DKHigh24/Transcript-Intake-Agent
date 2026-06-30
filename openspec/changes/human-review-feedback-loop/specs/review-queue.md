# Spec: Review Queue

## Purpose

Provide a persistent, auditable queue of classified opportunities awaiting human
review before Azure DevOps publication.

## Requirements

### Requirement: Queue created after classification

**WHEN** `--mode weekly` completes classification and validation
**THEN** a `queue.json` file SHALL be written to `output/review_queue/<date>/`
containing one item per primary classified row.

Each queue item SHALL include:
- `id`: a slug of the opportunity title
- `status`: initial value `"pending"` for all items
- `action_history`: empty list

### Requirement: Queue persists between runs

**WHEN** `--mode weekly` is re-run for the same date
**THEN** existing queue items that already have `review_status != null` SHALL NOT
be overwritten. Only new rows absent from the queue SHALL be added.

### Requirement: Review CLI works interactively

**WHEN** `--mode review --date <YYYY-MM-DD>` is run
**THEN** the CLI SHALL:
1. Load `output/review_queue/<date>/queue.json`
2. Present each pending item with: title, evidence summary, top classification fields
3. Prompt for action: `[A]pprove / [R]eject / [E]dit / [K]eep pending / [Q]uit`
4. Execute the action and update both `queue.json` and the archived `classified_rows.json`
5. Append to `feedback_log.jsonl`

### Requirement: Edit action validates against choice values

**WHEN** a reviewer edits a choice field
**THEN** `review_queue.py` SHALL validate the new value against `config/choice_values.json`
**AND** SHALL reject invalid values with a printed error without advancing the item

### Requirement: Model values are preserved

**WHEN** a reviewer edits any field
**THEN** the original model-generated value for that field SHALL remain in `row["_model"]`
**AND** the working field value SHALL be updated to the reviewer's value

### Requirement: Rows written back to archive

**WHEN** the review session completes (user quits or all items processed)
**THEN** review fields SHALL be written back to `output/weeks/<date>/classified_rows.json`
so that subsequent runs of `--mode weekly`, `--push-ado`, or report rebuilds see the
approved state.

## Non-functional

- Queue operations SHALL be deterministic Python (no AI calls)
- Queue files are human-readable JSON
- Re-running `--mode review` on a completed queue SHALL print "All items reviewed"
  and exit gracefully
