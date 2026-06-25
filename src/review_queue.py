"""
review_queue.py
Manages the per-week human review queue for classified opportunities.

Queue state is persisted to output/review_queue/<date>/queue.json.
All action handlers validate inputs, update queue state, and return the
modified item. Feedback log writes are handled by feedback_store (called
by the integration in main.py).

Public API:
    queue_path(date)                  -> Path
    load_queue(date)                  -> list[dict]
    save_queue(date, items)           -> None
    build_queue_from_rows(rows, date) -> list[dict]
    get_pending(items)                -> list[dict]
    action_approve(item, reviewer_id, notes)       -> dict
    action_reject(item, reviewer_id, reason)       -> dict
    action_edit(item, reviewer_id, field, value, notes) -> dict | None (None = validation fail)
    action_requeue(item, reviewer_id, notes)       -> dict
    apply_queue_to_rows(rows, items)  -> list[dict]
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import feedback_store

_QUEUE_BASE = Path("output") / "review_queue"
_CONFIG_DIR = Path(__file__).parent.parent / "config"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_choice_values() -> dict:
    p = _CONFIG_DIR / "choice_values.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _slugify(title: str) -> str:
    """Convert a title to a URL-safe slug for use as queue item ID."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:80]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Path helpers ─────────────────────────────────────────────────────────────

def queue_path(date: str) -> Path:
    """Return path to queue.json for the given date string (YYYY-MM-DD)."""
    return _QUEUE_BASE / date / "queue.json"


# ── Load / save ──────────────────────────────────────────────────────────────

def load_queue(date: str) -> list[dict]:
    """Load queue items for the given date, or return empty list."""
    p = queue_path(date)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("items", [])


def save_queue(date: str, items: list[dict]) -> None:
    """Persist queue items for the given date."""
    p = queue_path(date)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "updated_at": _now_iso(),
        "items": items,
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Build ─────────────────────────────────────────────────────────────────────

def build_queue_from_rows(rows: list[dict], date: str) -> list[dict]:
    """
    Create or update queue items from classified rows.

    Existing items whose status is not 'pending' are left untouched (preserving
    approved/rejected state across re-runs). New rows not yet in the queue are
    appended as pending.
    """
    existing = load_queue(date)
    existing_ids = {item["id"] for item in existing}

    for row in rows:
        item_id = _slugify(row.get("Title", "untitled"))
        if item_id in existing_ids:
            continue
        existing.append({
            "id": item_id,
            "title": row.get("Title", ""),
            "status": "pending",
            "action_history": [],
        })
        existing_ids.add(item_id)

    save_queue(date, existing)
    return existing


def get_pending(items: list[dict]) -> list[dict]:
    """Return items with status == 'pending'."""
    return [it for it in items if it.get("status") == "pending"]


# ── Action helpers ────────────────────────────────────────────────────────────

def _append_action(item: dict, entry: dict) -> dict:
    item.setdefault("action_history", []).append(entry)
    return item


def action_approve(item: dict, reviewer_id: str, notes: str = "",
                   date: str = "") -> dict:
    """Mark item as approved and log to feedback store."""
    ts = _now_iso()
    item["status"] = "approved"
    _append_action(item, {
        "action": "approve",
        "reviewer_id": reviewer_id,
        "timestamp": ts,
        "notes": notes or None,
    })
    feedback_store.record_approve(item["id"], date, reviewer_id, ts, notes or None)
    return item


def action_reject(item: dict, reviewer_id: str, reason: str = "",
                  date: str = "") -> dict:
    """Mark item as rejected and log to feedback store."""
    ts = _now_iso()
    item["status"] = "rejected"
    _append_action(item, {
        "action": "reject",
        "reviewer_id": reviewer_id,
        "timestamp": ts,
        "notes": reason or None,
    })
    feedback_store.record_reject(item["id"], date, reviewer_id, ts, reason or None)
    return item


def action_edit(
    item: dict,
    reviewer_id: str,
    field: str,
    new_value: Any,
    notes: str = "",
    date: str = "",
    model_value: Any = "<unknown>",
) -> dict | None:
    """
    Record a field edit on the item.  For choice fields, validates that
    new_value is in the allowed list.  Returns None if validation fails.

    The caller is responsible for writing new_value back to the classified row.
    """
    choices = _load_choice_values()
    if field in choices:
        if new_value not in choices[field]:
            print(f"  [review] Invalid value '{new_value}' for '{field}'.")
            print(f"  Allowed: {', '.join(choices[field])}")
            return None

    ts = _now_iso()
    _append_action(item, {
        "action": "edit",
        "field": field,
        "from": model_value,
        "to": new_value,
        "reviewer_id": reviewer_id,
        "timestamp": ts,
        "notes": notes or None,
    })
    item.setdefault("_field_values", {})[field] = new_value
    feedback_store.record_field_edit(
        item["id"], date, field,
        str(model_value), str(new_value),
        reviewer_id, ts, notes or None,
    )
    return item


def action_requeue(item: dict, reviewer_id: str, notes: str = "",
                   date: str = "") -> dict:
    """Return item to 'needs_reprocess' status and log to feedback store."""
    ts = _now_iso()
    item["status"] = "needs_reprocess"
    _append_action(item, {
        "action": "requeue",
        "reviewer_id": reviewer_id,
        "timestamp": ts,
        "notes": notes or None,
    })
    feedback_store.record_requeue(item["id"], date, reviewer_id, ts, notes or None)
    return item


# ── Apply queue state back to rows ────────────────────────────────────────────

def apply_queue_to_rows(rows: list[dict], items: list[dict]) -> list[dict]:
    """
    Write review_status, reviewer_id, reviewer_timestamp, and reviewer_notes
    from queue items back onto the corresponding classified rows.

    Matching is done by slugified Title.
    """
    id_to_item = {it["id"]: it for it in items}

    for row in rows:
        item_id = _slugify(row.get("Title", "untitled"))
        item = id_to_item.get(item_id)
        if not item:
            continue

        status = item.get("status")
        if status == "pending":
            continue  # no review action yet

        row["review_status"] = status

        # Find the most recent approve/reject/requeue action for attribution
        for entry in reversed(item.get("action_history", [])):
            if entry.get("action") in ("approve", "reject", "requeue"):
                row["reviewer_id"] = entry.get("reviewer_id")
                row["reviewer_timestamp"] = entry.get("timestamp")
                row["reviewer_notes"] = entry.get("notes")
                break

        # Apply any field edits accumulated in this review session
        for entry in item.get("action_history", []):
            if entry.get("action") == "edit":
                field = entry.get("field")
                value = entry.get("to")
                if field and field in row:
                    row[field] = value

    return rows
