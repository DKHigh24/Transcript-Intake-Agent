"""
backfill_tighten.py

Retroactively applies the tighten-extraction-signal post-processing to all
archived classified_rows.json files WITHOUT re-running any LLM calls.

Steps applied per week:
  1. Fuzzy dedup  — collapse near-duplicate classified rows using the same
                    SequenceMatcher threshold as candidate_deduplicator.py
  2. Confidence floor — rows with ConfidenceLevel == "Low" are removed from
                        the primary set (they go to a separate triage list that
                        is NOT written back to classified_rows.json, preserving
                        the master as primary-only rows)
  3. Session cap  — if primary rows still exceed MAX_CANDIDATES_PER_SESSION,
                    remove the lowest-confidence excess (same ordering used in
                    main.py step 4b)

Does NOT touch the 6/17 week (already run through tightened extraction).
Rebuilds master_opportunities.xlsx after all weeks are processed.
"""

import json
import os
import sys
from difflib import SequenceMatcher
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
WEEKS_DIR = Path("output/weeks")
THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.72"))
MAX_PRIMARY = int(os.getenv("MAX_CANDIDATES_PER_SESSION", "20"))
SKIP_WEEK = "2026-06-17"          # already clean — skip

CONF_ORDER = {"Low": 0, "Medium": 1, "High": 2}


# ── Dedup (adapted for classified rows) ───────────────────────────────────────

def _sim(a: dict, b: dict) -> float:
    ta = f"{a.get('Title', '')} {a.get('EvidenceSummary', '')}".lower().strip()
    tb = f"{b.get('Title', '')} {b.get('EvidenceSummary', '')}".lower().strip()
    return SequenceMatcher(None, ta, tb).ratio()


def _pick_winner(a: dict, b: dict) -> tuple[dict, dict]:
    la = len(a.get("EvidenceSummary") or "")
    lb = len(b.get("EvidenceSummary") or "")
    return (b, a) if lb > la else (a, b)


def dedup_classified(rows: list[dict], threshold: float) -> tuple[list[dict], int]:
    """Return (deduped_rows, n_removed)."""
    if len(rows) <= 1:
        return rows, 0

    remaining = list(rows)
    changed = True
    removed = 0

    while changed:
        changed = False
        skip = set()
        for i in range(len(remaining)):
            if i in skip:
                continue
            for j in range(i + 1, len(remaining)):
                if j in skip:
                    continue
                if _sim(remaining[i], remaining[j]) >= threshold:
                    keeper, _ = _pick_winner(remaining[i], remaining[j])
                    remaining[i] = keeper
                    skip.add(j)
                    changed = True
                    removed += 1
        remaining = [c for idx, c in enumerate(remaining) if idx not in skip]

    return remaining, removed


# ── Main ──────────────────────────────────────────────────────────────────────

def process_week(week_dir: Path) -> dict:
    classified_path = week_dir / "classified_rows.json"
    if not classified_path.exists():
        return {"week": week_dir.name, "skipped": True, "reason": "no classified_rows.json"}

    rows = json.loads(classified_path.read_text(encoding="utf-8"))
    original_count = len(rows)

    # Step 1: dedup
    rows, n_dedup = dedup_classified(rows, THRESHOLD)

    # Step 2: confidence floor — separate Low confidence out
    primary = [r for r in rows if r.get("ConfidenceLevel") != "Low"]
    n_low = len(rows) - len(primary)
    rows = primary

    # Step 3: session cap — sort by confidence descending, drop excess
    n_cap = 0
    if len(rows) > MAX_PRIMARY:
        rows_sorted = sorted(rows, key=lambda r: CONF_ORDER.get(r.get("ConfidenceLevel", "Medium"), 1), reverse=True)
        rows = rows_sorted[:MAX_PRIMARY]
        n_cap = len(rows_sorted) - MAX_PRIMARY

    final_count = len(rows)

    # Write back
    classified_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "week": week_dir.name,
        "original": original_count,
        "after_dedup": original_count - n_dedup,
        "after_conf_floor": original_count - n_dedup - n_low,
        "after_cap": final_count,
        "removed_dedup": n_dedup,
        "removed_low_conf": n_low,
        "removed_cap": n_cap,
    }


def main():
    week_dirs = sorted([d for d in WEEKS_DIR.iterdir() if d.is_dir() and d.name != SKIP_WEEK])

    print(f"[backfill-tighten] Processing {len(week_dirs)} week(s) "
          f"(threshold={THRESHOLD}, cap={MAX_PRIMARY}, skip={SKIP_WEEK})\n")

    results = []
    for wd in week_dirs:
        result = process_week(wd)
        results.append(result)
        if result.get("skipped"):
            print(f"  {result['week']}  SKIPPED ({result.get('reason', '')})")
        else:
            delta = result["original"] - result["after_cap"]
            print(
                f"  {result['week']}  "
                f"{result['original']} → {result['after_cap']} rows  "
                f"(-{result['removed_dedup']} dedup, "
                f"-{result['removed_low_conf']} low-conf, "
                f"-{result['removed_cap']} cap)"
            )

    print("\n[backfill-tighten] Rebuilding master opportunities workbook...")
    sys.path.insert(0, str(Path(__file__).parent))
    from master_exporter import rebuild_master
    rebuild_master()

    print("\n[backfill-tighten] Done.")
    total_before = sum(r.get("original", 0) for r in results if not r.get("skipped"))
    total_after  = sum(r.get("after_cap", 0) for r in results if not r.get("skipped"))
    print(f"  Total across processed weeks: {total_before} → {total_after} primary rows")


if __name__ == "__main__":
    main()
