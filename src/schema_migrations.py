"""
schema_migrations.py
Applies forward-only migrations to classified row dicts so that rows written
before a schema version bump load cleanly alongside current rows.

All migrations are non-destructive: they only ADD missing fields with null/default
values. They never remove or rename existing fields.

Usage:
    from schema_migrations import migrate
    row = migrate(row)   # idempotent — safe to call on any row
"""

import copy
from typing import Any

CURRENT_VERSION = 3

# ── Review fields added in v2 ────────────────────────────────────────────────
_V2_REVIEW_FIELDS: dict[str, Any] = {
    "review_status": None,
    "reviewer_id": None,
    "reviewer_timestamp": None,
    "reviewer_notes": None,
    "_model": None,
}

_V3_WORKSTREAM_FIELDS: dict[str, Any] = {
    "WorkstreamType": "Unknown",
}


def _migrate_v1_to_v2(row: dict) -> dict:
    """
    Schema v1 -> v2: add review tracking fields and _model snapshot.
    Fields are only set if absent — existing values (from a partial migration
    or a row already reviewed) are never overwritten.
    """
    for field, default in _V2_REVIEW_FIELDS.items():
        if field not in row:
            row[field] = default
    return row


def _migrate_v2_to_v3(row: dict) -> dict:
    """
    Schema v2 -> v3: add WorkstreamType dimension for lifecycle semantics.
    """
    for field, default in _V3_WORKSTREAM_FIELDS.items():
        if field not in row:
            row[field] = default
    return row


# Ordered migration chain.  Key = source version, value = migration function.
_MIGRATIONS: dict[int, Any] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
}


def migrate(row: dict) -> dict:
    """
    Apply all pending migrations to *row* in version order and return the
    (possibly mutated) row.  Safe to call on already-current rows.
    """
    row_version = row.get("_schema_version", 1)
    for version in sorted(_MIGRATIONS):
        if row_version <= version:
            row = _MIGRATIONS[version](row)
            row["_schema_version"] = version + 1
            row_version = version + 1
    return row


def migrate_list(rows: list[dict]) -> list[dict]:
    """Migrate a list of rows in place, returning the same list."""
    for i, row in enumerate(rows):
        rows[i] = migrate(row)
    return rows
