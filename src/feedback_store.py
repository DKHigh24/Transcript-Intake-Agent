"""
feedback_store.py
Append-only JSONL log of every reviewer decision.

Each record is one JSON line in output/feedback/feedback_log.jsonl.
Records are never modified after write — the log is append-only.

Record schemas:

  Approve / Reject / Requeue:
  {
    "event": "approve" | "reject" | "requeue",
    "opportunity_id": "<slug>",
    "date": "<YYYY-MM-DD>",
    "reviewer_id": "<string>",
    "timestamp": "<ISO 8601>",
    "reviewer_notes": "<string | null>"
  }

  Field edit:
  {
    "event": "field_edit",
    "opportunity_id": "<slug>",
    "date": "<YYYY-MM-DD>",
    "field": "<field name>",
    "model_value": "<original model value>",
    "reviewer_value": "<corrected value>",
    "reviewer_id": "<string>",
    "timestamp": "<ISO 8601>",
    "reviewer_notes": "<string | null>"
  }

Public API:
    append(record)                  -> None
    load_all()                      -> list[dict]
    filter_by_action(action)        -> list[dict]
    filter_by_field(field)          -> list[dict]
    get_edit_pairs(field)           -> list[tuple[str, str]]
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

FEEDBACK_LOG_PATH = Path("output") / "feedback" / "feedback_log.jsonl"


def _reviewer_id() -> str:
    """Return reviewer identity from env, falling back to os.getlogin()."""
    rid = os.getenv("REVIEWER_ID", "").strip()
    if rid:
        return rid
    try:
        return os.getlogin()
    except Exception:
        return "unknown"


def append(record: dict) -> None:
    """Append one feedback record to the log. Creates file and dirs if needed."""
    FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_all() -> list[dict]:
    """Return all feedback records, oldest first."""
    if not FEEDBACK_LOG_PATH.exists():
        return []
    records = []
    for line in FEEDBACK_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def filter_by_action(action: str) -> list[dict]:
    """Return records whose 'event' field matches action."""
    return [r for r in load_all() if r.get("event") == action]


def filter_by_field(field: str) -> list[dict]:
    """Return field_edit records for a specific field."""
    return [
        r for r in load_all()
        if r.get("event") == "field_edit" and r.get("field") == field
    ]


def get_edit_pairs(field: str) -> list[tuple[str, str]]:
    """
    Return (model_value, reviewer_value) pairs for all edits to a given field.
    Useful for building few-shot examples.
    """
    return [
        (r.get("model_value", ""), r.get("reviewer_value", ""))
        for r in filter_by_field(field)
    ]


# ── Convenience builders ──────────────────────────────────────────────────────

def record_approve(opportunity_id: str, date: str, reviewer_id: str,
                   timestamp: str, notes: str | None = None) -> None:
    append({
        "event": "approve",
        "opportunity_id": opportunity_id,
        "date": date,
        "reviewer_id": reviewer_id,
        "timestamp": timestamp,
        "reviewer_notes": notes,
    })


def record_reject(opportunity_id: str, date: str, reviewer_id: str,
                  timestamp: str, notes: str | None = None) -> None:
    append({
        "event": "reject",
        "opportunity_id": opportunity_id,
        "date": date,
        "reviewer_id": reviewer_id,
        "timestamp": timestamp,
        "reviewer_notes": notes,
    })


def record_requeue(opportunity_id: str, date: str, reviewer_id: str,
                   timestamp: str, notes: str | None = None) -> None:
    append({
        "event": "requeue",
        "opportunity_id": opportunity_id,
        "date": date,
        "reviewer_id": reviewer_id,
        "timestamp": timestamp,
        "reviewer_notes": notes,
    })


def record_field_edit(opportunity_id: str, date: str, field: str,
                      model_value: str, reviewer_value: str,
                      reviewer_id: str, timestamp: str,
                      notes: str | None = None) -> None:
    append({
        "event": "field_edit",
        "opportunity_id": opportunity_id,
        "date": date,
        "field": field,
        "model_value": str(model_value),
        "reviewer_value": str(reviewer_value),
        "reviewer_id": reviewer_id,
        "timestamp": timestamp,
        "reviewer_notes": notes,
    })
