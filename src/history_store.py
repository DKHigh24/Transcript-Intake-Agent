"""
history_store.py
Cumulative store of AI opportunities tracked across weekly transcript uploads.

Each history entry tracks one opportunity over time:
    {
      "key": "<slug>",
      "title": "<canonical title>",
      "aliases": ["<other titles seen>"],
      "first_seen": "YYYY-MM-DD",
      "last_seen": "YYYY-MM-DD",
      "occurrences": [ { "date", "week", "month", ...snapshot fields... }, ... ]
    }

Ingesting a week is idempotent by meeting date: re-ingesting the same date first
removes that date's occurrences, then re-adds them, so re-runs do not double-count.
"""

import json
from datetime import date
from pathlib import Path

from period_utils import HISTORY_PATH, period_info, ensure_dirs
from opportunity_matcher import find_match, stable_key

# Fields captured per occurrence (a weekly snapshot of the opportunity).
_SNAPSHOT_FIELDS = [
    "Title",
    "ProblemPainPoint",
    "OperatingBucket",
    "ProcessStage",
    "AIUseCaseType",
    "PrimaryFunctionChoice",
    "LevelOfAnalysis",
    "SignalStrength",
    "PrimaryTool",
    "ConfidenceLevel",
    "ValueScore",
    "EffortScore",
    "RiskScore",
    "ReadinessScore",
    "SignalScore",
    "NextStep",
    "EvidenceSummary",
    "SourceSpeaker",
    "SourceTimestamp",
    "SuggestedBusinessOwnerText",
    "SuggestedSMEChampionText",
]


def load_history(path: Path = HISTORY_PATH) -> list[dict]:
    """Load the cumulative opportunity history. Returns [] if none exists yet."""
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return []


def save_history(history: list[dict], path: Path = HISTORY_PATH) -> None:
    ensure_dirs()
    Path(path).write_text(json.dumps(history, indent=2), encoding="utf-8")


def _make_snapshot(row: dict, period: dict) -> dict:
    snap = {"date": period["date"], "week": period["week"], "month": period["month"]}
    for f in _SNAPSHOT_FIELDS:
        if f in row:
            snap[f] = row[f]
    return snap


def _dedup_week_rows(rows: list[dict]) -> list[dict]:
    """Collapse rows within a single week that describe the same opportunity."""
    deduped: list[dict] = []
    for row in rows:
        title = row.get("Title", "")
        if not title:
            continue
        existing = next(
            (r for r in deduped if find_match(title, [{"title": r.get("Title", "")}])),
            None,
        )
        if existing is None:
            deduped.append(row)
    return deduped


def ingest_week(
    rows: list[dict],
    meeting_date: date,
    path: Path = HISTORY_PATH,
) -> list[dict]:
    """
    Merge one week's classified rows into the cumulative history.

    Idempotent by meeting date. Returns the updated history list.
    """
    period = period_info(meeting_date)
    history = load_history(path)

    # Idempotency: drop any existing occurrences for this date, then prune empties.
    for entry in history:
        entry["occurrences"] = [
            o for o in entry.get("occurrences", []) if o.get("date") != period["date"]
        ]

    for row in _dedup_week_rows(rows):
        title = row.get("Title", "")
        if not title:
            continue
        snapshot = _make_snapshot(row, period)

        match = find_match(title, history)
        if match is None:
            history.append({
                "key": stable_key(title),
                "title": title,
                "aliases": [],
                "first_seen": period["date"],
                "last_seen": period["date"],
                "occurrences": [snapshot],
            })
        else:
            if title != match["title"] and title not in match.setdefault("aliases", []):
                match["aliases"].append(title)
            match["occurrences"].append(snapshot)

    # Recompute first/last seen and drop entries that ended up empty.
    cleaned: list[dict] = []
    for entry in history:
        occ = sorted(entry.get("occurrences", []), key=lambda o: o["date"])
        if not occ:
            continue
        entry["occurrences"] = occ
        entry["first_seen"] = occ[0]["date"]
        entry["last_seen"] = occ[-1]["date"]
        cleaned.append(entry)

    cleaned.sort(key=lambda e: (-len(e["occurrences"]), e["title"].lower()))
    save_history(cleaned, path)
    return cleaned
