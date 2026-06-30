# Spec: Feedback Store

## Purpose

Capture every reviewer decision as a structured, immutable log record to enable
future prompt improvement, evaluation, and audit.

## Requirements

### Requirement: Every reviewer action is logged

**WHEN** a reviewer approves, rejects, or edits an opportunity
**THEN** a JSON record SHALL be appended to `output/feedback/feedback_log.jsonl`

For approve/reject records:
```json
{
  "event": "approve" | "reject",
  "opportunity_id": "<slug>",
  "date": "<YYYY-MM-DD>",
  "reviewer_id": "<reviewer>",
  "timestamp": "<ISO 8601>",
  "reviewer_notes": "<string | null>"
}
```

For field edit records:
```json
{
  "event": "field_edit",
  "opportunity_id": "<slug>",
  "date": "<YYYY-MM-DD>",
  "field": "<field name>",
  "model_value": "<original value>",
  "reviewer_value": "<corrected value>",
  "reviewer_id": "<reviewer>",
  "timestamp": "<ISO 8601>",
  "reviewer_notes": "<string | null>"
}
```

### Requirement: Log is append-only

**WHEN** `feedback_store.append(record)` is called
**THEN** the record SHALL be written as a single JSON line to the end of the file
**AND** no existing records SHALL be modified

### Requirement: Reviewer identity is captured

**WHEN** any feedback record is written
**THEN** `reviewer_id` SHALL be populated from `REVIEWER_ID` environment variable
**AND** if `REVIEWER_ID` is not set, `os.getlogin()` SHALL be used as fallback

### Requirement: Feedback survives pipeline re-runs

**WHEN** `--mode weekly` is re-run for the same date
**THEN** the feedback log SHALL NOT be cleared or overwritten
**AND** previously logged records SHALL remain intact

### Requirement: Feedback is queryable

`feedback_store.py` SHALL provide:
- `load_all() -> list[dict]`
- `filter_by_action(action: str) -> list[dict]`
- `filter_by_field(field: str) -> list[dict]`
- `get_edit_pairs(field: str) -> list[tuple[str, str]]`

## Non-functional

- The file is gitignored (may contain reviewer names and timestamps)
- The file is human-readable JSONL — one record per line, no wrapping
- The feedback store has no dependency on any database or external service
