"""
backfill_workstream_type.py

One-time deterministic backfill for WorkstreamType across archived weeks.

What it does:
  1) Loads every output/weeks/<YYYY-MM-DD>/classified_rows.json
  2) Migrates rows to schema v3 (adds WorkstreamType where missing)
  3) Infers WorkstreamType from OperatingBucket/ProcessStage/SubOrdinateFunction/text
  4) Writes updated classified_rows.json files in-place
  5) Rebuilds output/history/opportunities.json from archived weeks so snapshots
     include WorkstreamType
  6) Rebuilds output/master_opportunities.xlsx

Usage:
  python src/backfill_workstream_type.py
  python src/backfill_workstream_type.py --dry-run
  python src/backfill_workstream_type.py --force
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from history_store import ingest_week, save_history, HISTORY_PATH
from master_exporter import rebuild_master
from schema_migrations import migrate

WEEKS_DIR = Path("output/weeks")
VALID_WORKSTREAMS = {"Transactional", "Product Vitality", "Governance", "Support", "Unknown"}

_OPERATING_BUCKET_ALIASES = {
    "Crosss-Functional/Governance": "Cross-Functional/Governance",
    "Cross-Functional / Governance": "Cross-Functional/Governance",
}


def _norm(value) -> str:
    return str(value or "").strip()


def _norm_bucket(value: str) -> str:
    return _OPERATING_BUCKET_ALIASES.get(value, value)


def _infer_workstream_type(row: dict) -> str:
    bucket = _norm_bucket(_norm(row.get("OperatingBucket")))
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

    if bucket in ("Cross-Functional/Governance",) or stage == "Governance/Intake":
        return "Governance"
    if sub_fn in ("AI Opportunity Intake", "Policy Enforcement", "Review Board"):
        return "Governance"

    product_sub_fn_markers = (
        "NPD - New Product Development",
        "Engineering Design",
        "Engineering Change Orders (ECO)",
        "Software / Firmware Updates",
        "Design Updates",
        "Prototyping",
        "Design Review",
    )
    product_stage_markers = ("Solution Development",)
    product_text_markers = (
        "firmware",
        "software",
        "hardware",
        "product vitality",
        "continuous improvement",
        "platform",
        "refactor",
        "reliability",
        "performance",
        "new product",
    )
    if bucket == "Engineering / Product Vitality":
        return "Product Vitality"
    if sub_fn in product_sub_fn_markers or stage in product_stage_markers:
        return "Product Vitality"
    if any(marker in text_blob for marker in product_text_markers):
        return "Product Vitality"

    support_stage_markers = (
        "Incident Identification",
        "Sustaining Engineering",
        "Sustaining Solution",
        "Resolution",
        "Feedback",
    )
    support_sub_fn_markers = (
        "Technical Support",
        "Field Service",
        "Warranty Claims",
        "Field Reports",
        "Customer Complaints",
        "Ongoing Maintenance",
        "Ongoing Support",
        "Root Cause Analysis",
        "Corrective Action",
        "Escalation",
    )
    if stage in support_stage_markers or sub_fn in support_sub_fn_markers:
        return "Support"

    transactional_buckets = ("Outside/Pre-Sale", "Inside/Pre-Sale", "Manufacturing", "Post Shipment")
    transactional_stage_markers = (
        "Opportunities",
        "Solution Approval",
        "Order Validation",
        "Order Creation",
        "Order Activation",
        "Production",
        "Delivery",
        "Installation",
        "Deployment",
        "Solution Implementation",
    )
    if bucket in transactional_buckets or stage in transactional_stage_markers:
        return "Transactional"

    return "Unknown"


def _should_update(existing: str, inferred: str, force: bool) -> bool:
    if force:
        return existing != inferred
    if not existing:
        return True
    if existing not in VALID_WORKSTREAMS:
        return True
    if existing == "Unknown" and inferred != "Unknown":
        return True
    return False


def _process_week(week_dir: Path, *, dry_run: bool, force: bool) -> tuple[int, int]:
    path = week_dir / "classified_rows.json"
    if not path.exists():
        return (0, 0)

    rows = json.loads(path.read_text(encoding="utf-8"))
    touched = 0
    total = len(rows)
    out_rows = []

    for row in rows:
        migrated = migrate(dict(row))
        existing = _norm(migrated.get("WorkstreamType"))
        inferred = _infer_workstream_type(migrated)
        if _should_update(existing, inferred, force):
            migrated["WorkstreamType"] = inferred
            touched += 1
        out_rows.append(migrated)

    if touched and not dry_run:
        path.write_text(json.dumps(out_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return (total, touched)


def _rebuild_history_from_weeks(*, dry_run: bool) -> int:
    week_dirs = sorted([d for d in WEEKS_DIR.glob("????-??-??") if d.is_dir()])
    if dry_run:
        return len(week_dirs)

    if HISTORY_PATH.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = HISTORY_PATH.parent / f"opportunities.backup-{stamp}.json"
        backup_path.write_text(HISTORY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[backfill-workstream] history backup -> {backup_path}")

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
    parser = argparse.ArgumentParser(description="Backfill WorkstreamType on archived rows")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only; do not write files")
    parser.add_argument("--force", action="store_true", help="Recompute even when WorkstreamType is already set")
    args = parser.parse_args()

    week_dirs = sorted([d for d in WEEKS_DIR.glob("????-??-??") if d.is_dir()])
    print(f"[backfill-workstream] scanning {len(week_dirs)} week(s) (dry-run={args.dry_run}, force={args.force})")

    total_rows = 0
    total_updated = 0
    for week_dir in week_dirs:
        total, touched = _process_week(week_dir, dry_run=args.dry_run, force=args.force)
        total_rows += total
        total_updated += touched
        if total:
            print(f"  {week_dir.name}: {touched}/{total} row(s) updated")

    ingested = _rebuild_history_from_weeks(dry_run=args.dry_run)
    print(f"[backfill-workstream] history rebuild weeks: {ingested}")

    if not args.dry_run:
        rebuild_master()
        print("[backfill-workstream] master workbook rebuilt")

    print(
        f"[backfill-workstream] done — {total_updated} updated across {total_rows} row(s) "
        f"in {len(week_dirs)} week(s)"
    )


if __name__ == "__main__":
    main()
