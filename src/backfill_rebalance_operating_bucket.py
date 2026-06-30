"""
backfill_rebalance_operating_bucket.py

One-time deterministic rebalance for OperatingBucket across archived weeks.

Goal:
  Move engineering/product-vitality work out of Cross-Functional/Governance into
  Engineering / Product Vitality without re-running model calls.

Usage:
  python src/backfill_rebalance_operating_bucket.py
  python src/backfill_rebalance_operating_bucket.py --dry-run
  python src/backfill_rebalance_operating_bucket.py --force
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from history_store import ingest_week, save_history, HISTORY_PATH
from master_exporter import rebuild_master
from schema_migrations import migrate

WEEKS_DIR = Path("output/weeks")

_BUCKET_ALIAS = {
    "Crosss-Functional/Governance": "Cross-Functional/Governance",
    "Cross-Functional / Governance": "Cross-Functional/Governance",
}

ENGINEERING_STAGE_MARKERS = {
    "Solution Development",
    "Sustaining Engineering",
}
ENGINEERING_SUBFN_MARKERS = {
    "NPD - New Product Development",
    "Engineering Design",
    "Engineering Change Orders (ECO)",
    "Software / Firmware Updates",
    "Design Updates",
    "Prototyping",
    "Design Review",
}
ENGINEERING_TEXT_MARKERS = (
    "firmware",
    "software",
    "hardware",
    "product vitality",
    "continuous improvement",
    "platform",
    "engineering",
    "refactor",
    "reliability",
    "performance",
    "new product",
)


def _norm(value) -> str:
    return str(value or "").strip()


def _canonical_bucket(bucket: str) -> str:
    return _BUCKET_ALIAS.get(bucket, bucket)


def _looks_product_vitality(row: dict) -> bool:
    workstream = _norm(row.get("WorkstreamType"))
    stage = _norm(row.get("ProcessStage"))
    sub_fn = _norm(row.get("SubOrdinateFunction"))
    text_blob = " ".join(
        [
            _norm(row.get("Title")).lower(),
            _norm(row.get("ProblemPainPoint")).lower(),
            _norm(row.get("EvidenceSummary")).lower(),
            _norm(row.get("NextStep")).lower(),
        ]
    )

    if workstream == "Product Vitality":
        return True
    if stage in ENGINEERING_STAGE_MARKERS:
        return True
    if sub_fn in ENGINEERING_SUBFN_MARKERS:
        return True
    return any(marker in text_blob for marker in ENGINEERING_TEXT_MARKERS)


def _process_week(week_dir: Path, *, dry_run: bool, force: bool) -> tuple[int, int, int]:
    rows_path = week_dir / "classified_rows.json"
    if not rows_path.exists():
        return (0, 0, 0)

    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    total = len(rows)
    normalized = 0
    rebalanced = 0
    out_rows = []

    for row in rows:
        migrated = migrate(dict(row))
        current_bucket = _canonical_bucket(_norm(migrated.get("OperatingBucket")))
        if current_bucket != _norm(migrated.get("OperatingBucket")):
            migrated["OperatingBucket"] = current_bucket
            normalized += 1

        should_rebalance = _looks_product_vitality(migrated)
        if current_bucket == "Cross-Functional/Governance" and should_rebalance:
            migrated["OperatingBucket"] = "Engineering / Product Vitality"
            rebalanced += 1
        elif force and should_rebalance and current_bucket != "Engineering / Product Vitality":
            migrated["OperatingBucket"] = "Engineering / Product Vitality"
            rebalanced += 1

        out_rows.append(migrated)

    if (normalized or rebalanced) and not dry_run:
        rows_path.write_text(json.dumps(out_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return (total, normalized, rebalanced)


def _rebuild_history_from_weeks(*, dry_run: bool) -> int:
    week_dirs = sorted([d for d in WEEKS_DIR.glob("????-??-??") if d.is_dir()])
    if dry_run:
        return len(week_dirs)

    if HISTORY_PATH.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = HISTORY_PATH.parent / f"opportunities.backup-rebalance-{stamp}.json"
        backup_path.write_text(HISTORY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[rebalance-bucket] history backup -> {backup_path}")

    save_history([])
    ingested = 0
    for week_dir in week_dirs:
        rows_path = week_dir / "classified_rows.json"
        if not rows_path.exists():
            continue
        rows = json.loads(rows_path.read_text(encoding="utf-8"))
        meeting_date = datetime.strptime(week_dir.name, "%Y-%m-%d").date()
        ingest_week(rows, meeting_date)
        ingested += 1
    return ingested


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance OperatingBucket for archived rows")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only; do not write files")
    parser.add_argument("--force", action="store_true", help="Also move non-governance engineering rows into Product Vitality")
    args = parser.parse_args()

    week_dirs = sorted([d for d in WEEKS_DIR.glob("????-??-??") if d.is_dir()])
    print(f"[rebalance-bucket] scanning {len(week_dirs)} week(s) (dry-run={args.dry_run}, force={args.force})")

    total_rows = 0
    total_norm = 0
    total_rebalanced = 0
    for week_dir in week_dirs:
        total, normalized, rebalanced = _process_week(week_dir, dry_run=args.dry_run, force=args.force)
        total_rows += total
        total_norm += normalized
        total_rebalanced += rebalanced
        if total:
            print(f"  {week_dir.name}: normalized={normalized}, rebalanced={rebalanced}, rows={total}")

    ingested = _rebuild_history_from_weeks(dry_run=args.dry_run)
    print(f"[rebalance-bucket] history rebuild weeks: {ingested}")

    if not args.dry_run:
        rebuild_master()
        print("[rebalance-bucket] master workbook rebuilt")

    print(
        f"[rebalance-bucket] done — normalized={total_norm}, rebalanced={total_rebalanced} "
        f"across {total_rows} row(s)"
    )


if __name__ == "__main__":
    main()
