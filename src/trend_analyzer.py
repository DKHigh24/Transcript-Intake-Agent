"""
trend_analyzer.py
Computes longitudinal trend metrics from the cumulative opportunity history
produced by history_store.py. Pure functions only — no I/O, no AI.

Two entry points:
  - weekly_analysis(history, meeting_date): metrics for one week (new vs recurring,
    deltas vs the prior week, recent-week counts).
  - monthly_analysis(history, month): rollups across all weeks within a month.
"""

from collections import Counter, defaultdict
from datetime import date

from period_utils import iso_week_label, month_label, date_label

# Ordered choice scales used to detect "escalation" (movement up the scale).
_SIGNAL_ORDER = [
    "Isolated Example",
    "Repeated within One Team",
    "Repeated Across Multiple Teams",
    "Cross-Functional Pattern",
]
_LEVEL_ORDER = [
    "Level 0 - Signal Capture",
    "Level 1 - Categorization",
    "Level 2 - Descriptive Analysis",
    "Level 3 - Diagnostic Analysis",
    "Level 4 - Predictive/Risk Analysis",
    "Level 5 - Prescriptive Recommendation",
    "Leve 6 - Action/Automation",
    "Level 7 - Release Candidate",
]


def _rank(order: list[str], value) -> int:
    try:
        return order.index(value)
    except (ValueError, TypeError):
        return -1


# ── shared helpers ────────────────────────────────────────────────────────────

def all_dates(history: list[dict]) -> list[str]:
    dates = {o["date"] for e in history for o in e["occurrences"]}
    return sorted(dates)


def entries_for_date(history: list[dict], d: str) -> list[dict]:
    """History entries that have an occurrence on date `d`, paired with that snapshot."""
    out = []
    for e in history:
        snap = next((o for o in e["occurrences"] if o["date"] == d), None)
        if snap:
            out.append((e, snap))
    return out


def _distribution(snaps: list[dict], field: str) -> dict:
    return dict(Counter(s.get(field, "Unknown") for s in snaps))


# ── weekly analysis ───────────────────────────────────────────────────────────

def weekly_analysis(history: list[dict], meeting_date: date) -> dict:
    """Metrics describing a single week relative to prior weeks."""
    d = date_label(meeting_date)
    dates = all_dates(history)
    prior_dates = [x for x in dates if x < d]
    prev_date = prior_dates[-1] if prior_dates else None

    this_week = entries_for_date(history, d)
    snaps = [snap for _, snap in this_week]

    new_items, recurring_items, escalations = [], [], []
    for entry, snap in this_week:
        occ_dates = [o["date"] for o in entry["occurrences"]]
        is_new = min(occ_dates) == d
        record = {
            "key": entry["key"],
            "title": snap.get("Title", entry["title"]),
            "bucket": snap.get("OperatingBucket", ""),
            "type": snap.get("AIUseCaseType", ""),
            "signal": snap.get("SignalStrength", ""),
            "level": snap.get("LevelOfAnalysis", ""),
            "confidence": snap.get("ConfidenceLevel", ""),
            "occurrences": len(entry["occurrences"]),
            "next_step": snap.get("NextStep", ""),
            "evidence": snap.get("EvidenceSummary", ""),
            "speaker": snap.get("SourceSpeaker", ""),
        }
        if is_new:
            new_items.append(record)
        else:
            prev_snap = max(
                (o for o in entry["occurrences"] if o["date"] < d),
                key=lambda o: o["date"],
                default=None,
            )
            signal_delta = level_delta = 0
            if prev_snap:
                signal_delta = _rank(_SIGNAL_ORDER, snap.get("SignalStrength")) - \
                    _rank(_SIGNAL_ORDER, prev_snap.get("SignalStrength"))
                level_delta = _rank(_LEVEL_ORDER, snap.get("LevelOfAnalysis")) - \
                    _rank(_LEVEL_ORDER, prev_snap.get("LevelOfAnalysis"))
            record["signal_delta"] = signal_delta
            record["level_delta"] = level_delta
            recurring_items.append(record)
            if signal_delta > 0 or level_delta > 0:
                escalations.append(record)

    # Recent-week totals for the mini trend line (last 8 weeks of data).
    week_counts = defaultdict(int)
    for x in dates:
        week_counts[x] = len(entries_for_date(history, x))
    recent = [{"date": x, "count": week_counts[x]} for x in dates][-8:]

    return {
        "date": d,
        "week": iso_week_label(meeting_date),
        "month": month_label(meeting_date),
        "prev_date": prev_date,
        "total": len(this_week),
        "new_count": len(new_items),
        "recurring_count": len(recurring_items),
        "escalation_count": len(escalations),
        "new_items": new_items,
        "recurring_items": recurring_items,
        "escalations": escalations,
        "bucket_distribution": _distribution(snaps, "OperatingBucket"),
        "type_distribution": _distribution(snaps, "AIUseCaseType"),
        "recent_weeks": recent,
        "cumulative_total": len(history),
    }


# ── monthly analysis ──────────────────────────────────────────────────────────

def monthly_analysis(history: list[dict], month: str) -> dict:
    """Rollups across every week within calendar `month` (e.g. '2026-06')."""
    month_dates = sorted({
        o["date"] for e in history for o in e["occurrences"]
        if o.get("month") == month
    })

    per_week = []
    bucket_by_week = defaultdict(lambda: defaultdict(int))
    seen_before_month = set()
    # Determine which opportunities first appeared before this month.
    for e in history:
        first = min((o["date"] for o in e["occurrences"]), default=None)
        if first and first[:7] < month:
            seen_before_month.add(e["key"])

    seen_in_month: set[str] = set()
    for d in month_dates:
        items = entries_for_date(history, d)
        new_this_week = 0
        for entry, snap in items:
            occ_dates = [o["date"] for o in entry["occurrences"]]
            if min(occ_dates) == d:
                new_this_week += 1
            bucket_by_week[d][snap.get("OperatingBucket", "Unknown")] += 1
            seen_in_month.add(entry["key"])
        per_week.append({
            "date": d,
            "total": len(items),
            "new": new_this_week,
            "recurring": len(items) - new_this_week,
        })

    # Opportunities active this month, ranked by total occurrences.
    active = []
    for e in history:
        month_occ = [o for o in e["occurrences"] if o.get("month") == month]
        if not month_occ:
            continue
        latest = max(month_occ, key=lambda o: o["date"])
        active.append({
            "key": e["key"],
            "title": e["title"],
            "bucket": latest.get("OperatingBucket", ""),
            "type": latest.get("AIUseCaseType", ""),
            "signal": latest.get("SignalStrength", ""),
            "level": latest.get("LevelOfAnalysis", ""),
            "total_occurrences": len(e["occurrences"]),
            "month_occurrences": len(month_occ),
            "first_seen": e["first_seen"],
            "last_seen": e["last_seen"],
            "is_carryover": e["key"] in seen_before_month,
        })
    active.sort(key=lambda a: (-a["total_occurrences"], a["title"].lower()))

    # Escalations within the month (signal or level moved up across the month).
    escalations = []
    for e in history:
        month_occ = sorted(
            (o for o in e["occurrences"] if o.get("month") == month),
            key=lambda o: o["date"],
        )
        if len(month_occ) < 2:
            continue
        s_delta = _rank(_SIGNAL_ORDER, month_occ[-1].get("SignalStrength")) - \
            _rank(_SIGNAL_ORDER, month_occ[0].get("SignalStrength"))
        l_delta = _rank(_LEVEL_ORDER, month_occ[-1].get("LevelOfAnalysis")) - \
            _rank(_LEVEL_ORDER, month_occ[0].get("LevelOfAnalysis"))
        if s_delta > 0 or l_delta > 0:
            escalations.append({
                "key": e["key"],
                "title": e["title"],
                "signal_from": month_occ[0].get("SignalStrength", ""),
                "signal_to": month_occ[-1].get("SignalStrength", ""),
                "level_from": month_occ[0].get("LevelOfAnalysis", ""),
                "level_to": month_occ[-1].get("LevelOfAnalysis", ""),
                "signal_delta": s_delta,
                "level_delta": l_delta,
            })
    escalations.sort(key=lambda x: -(x["signal_delta"] + x["level_delta"]))

    all_month_snaps = [
        o for e in history for o in e["occurrences"] if o.get("month") == month
    ]

    return {
        "month": month,
        "weeks_covered": len(month_dates),
        "week_dates": month_dates,
        "unique_total": len(seen_in_month),
        "new_total": len([a for a in active if not a["is_carryover"]]),
        "carryover_total": len([a for a in active if a["is_carryover"]]),
        "escalation_count": len(escalations),
        "per_week": per_week,
        "bucket_by_week": {d: dict(v) for d, v in bucket_by_week.items()},
        "type_distribution": _distribution(all_month_snaps, "AIUseCaseType"),
        "level_distribution": _distribution(all_month_snaps, "LevelOfAnalysis"),
        "active": active,
        "escalations": escalations,
    }
