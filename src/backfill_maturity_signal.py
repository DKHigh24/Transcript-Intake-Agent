"""
backfill_maturity_signal.py
Iterate all archived week classified_rows.json files and infer MaturitySignal
for any row where it is missing or empty. Updates the JSON in-place, then
triggers a master XLSX rebuild.

Usage:
    python src/backfill_maturity_signal.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is on path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import call_llm
from master_exporter import rebuild_master

WEEKS_DIR = Path("output/weeks")
VALID_SIGNALS = {
    "Aspirational",
    "In Progress / Piloting",
    "Delivered / Active Today",
    "Unknown",
}

SYSTEM_PROMPT = """You are a classification assistant for an AI opportunity registry.

Given an opportunity Title and EvidenceSummary from a meeting transcript, assign a
MaturitySignal using ONLY one of these four values:

  - Aspirational            — future-tense proposal, no delivery evidence
                              ("we should", "what if", "I'd love to see", "could we")
  - In Progress / Piloting  — actively being tested or evaluated
                              ("we're testing", "proof of concept", "in evaluation",
                               "we started", "we're exploring")
  - Delivered / Active Today — confirmed live and working today
                              ("we're already using", "this is live", "we deployed",
                               "it's in production", "we built this", "working today")
  - Unknown                 — evidence is ambiguous or contains no clear maturity marker

Respond with ONLY the exact value string (no punctuation, no explanation)."""


def _infer_signal(title: str, evidence: str) -> str:
    user_prompt = f"Title: {title}\nEvidenceSummary: {evidence or '(none)'}"
    raw = call_llm(SYSTEM_PROMPT, user_prompt).strip()
    # Normalise — strip quotes/periods the model might add
    raw = raw.strip('"\'.,').strip()
    for v in VALID_SIGNALS:
        if v.lower() in raw.lower():
            return v
    return "Unknown"


def backfill(dry_run: bool = False) -> dict[str, int]:
    week_dirs = sorted(WEEKS_DIR.iterdir())
    totals = {"weeks": 0, "rows_updated": 0, "rows_skipped": 0}

    for week_dir in week_dirs:
        rows_file = week_dir / "classified_rows.json"
        if not rows_file.exists():
            continue

        rows: list[dict] = json.loads(rows_file.read_text(encoding="utf-8"))
        needs_signal = [r for r in rows if not r.get("MaturitySignal")]

        if not needs_signal:
            print(f"[backfill] {week_dir.name}: all {len(rows)} rows already have MaturitySignal — skipped")
            totals["rows_skipped"] += len(rows)
            continue

        print(f"[backfill] {week_dir.name}: {len(needs_signal)}/{len(rows)} rows need MaturitySignal")
        totals["weeks"] += 1

        for row in needs_signal:
            title = row.get("Title", "")
            evidence = row.get("EvidenceSummary", "")
            signal = _infer_signal(title, evidence)
            print(f"  {title[:55]:55s} -> {signal}")
            if not dry_run:
                row["MaturitySignal"] = signal
            totals["rows_updated"] += 1

        if not dry_run:
            rows_file.write_text(
                json.dumps(rows, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  saved {rows_file}")

    return totals


def main():
    parser = argparse.ArgumentParser(description="Back-fill MaturitySignal on archived classified rows")
    parser.add_argument("--dry-run", action="store_true", help="Infer signals but do not write files")
    args = parser.parse_args()

    print("=== Back-fill MaturitySignal ===")
    totals = backfill(dry_run=args.dry_run)

    print(f"\n[backfill] Done — {totals['rows_updated']} rows updated across {totals['weeks']} week(s), "
          f"{totals['rows_skipped']} already complete")

    if not args.dry_run and totals["rows_updated"] > 0:
        print("\n=== Rebuilding master_opportunities.xlsx ===")
        rebuild_master()


if __name__ == "__main__":
    main()
