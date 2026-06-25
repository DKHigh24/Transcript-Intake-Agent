"""
main.py
CLI entrypoint for the AI Transcript Intake Agent.

Modes:
  dry-run  — Read, clean, chunk transcript → output/transcript_chunks.json
  extract  — dry-run + extract candidates  → output/candidates.json
  classify — extract + classify candidates → output/classified_rows.json
  payload  — classify + export workbook + build payload
  push     — payload + POST to Power Automate (requires ENABLE_POWER_AUTOMATE_PUSH=true)
  weekly   — payload + archive the week + ingest into history + weekly trend report
             (auto-rebuilds ALL reports when a back-dated transcript is detected)
             (also generates the upcoming session PPTX in output/meeting_presentations/)
  monthly  — build the monthly trend report from accumulated history
  rebuild  — regenerate every weekly and monthly report from current history
             (use after manual history edits or back-dated ingests)

Usage:
  python src/main.py --input input/transcripts/meeting.docx --mode dry-run
  python src/main.py --input input/transcripts/meeting.docx --mode payload
  python src/main.py --input input/transcripts/meeting.docx --mode push
  python src/main.py --input input/transcripts/meeting_6_3_2026.docx --mode weekly
  python src/main.py --input input/transcripts/meeting_6_3_2026.docx --mode monthly
  python src/main.py --mode monthly --month 2026-06
  python src/main.py --mode rebuild
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from transcript_reader import read_transcript
from transcript_cleaner import clean_paragraphs
from transcript_chunker import chunk_transcript
from candidate_detector import detect_candidates
from candidate_deduplicator import deduplicate_candidates
from classifier import classify_candidates
from validators import validate_all_rows
from review_exporter import export_review_workbook
from master_exporter import update_master
from power_automate_client import build_sharepoint_payload, push_to_power_automate
from mock_data import MOCK_CANDIDATES, MOCK_CLASSIFIED_ROWS
from report_generator import generate_report
import period_utils
from history_store import ingest_week, load_history
from trend_reporter import generate_weekly_report, generate_monthly_report

OUTPUT_DIR = Path("output")
CHUNKS_PATH = str(OUTPUT_DIR / "transcript_chunks.json")
CANDIDATES_PATH = str(OUTPUT_DIR / "candidates.json")
CLASSIFIED_PATH = str(OUTPUT_DIR / "classified_rows.json")
REVIEW_PATH = str(OUTPUT_DIR / "review_rows.xlsx")
PAYLOAD_PATH = str(OUTPUT_DIR / "sharepoint_payload.json")

MODES = ["dry-run", "extract", "classify", "payload", "push", "weekly", "monthly", "rebuild",
         "review", "apply-feedback", "eval", "promote-feedback"]

# ── Configurable thresholds (from .env, with defaults) ───────────────────────
_DEDUP_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.72"))
_MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES_PER_SESSION", "20"))


def run_dry_run(docx_path: str) -> list[dict]:
    print("\n=== Step 1: Read transcript ===")
    paragraphs = read_transcript(docx_path)
    print(f"  {len(paragraphs)} paragraphs read")

    print("\n=== Step 2: Clean transcript ===")
    cleaned = clean_paragraphs(paragraphs)
    print(f"  {len(cleaned)} cleaned paragraphs")

    print("\n=== Step 3: Chunk transcript ===")
    chunks = chunk_transcript(cleaned, CHUNKS_PATH)
    return chunks


def run_extract(docx_path: str, mock: bool = False) -> list[dict]:
    if mock:
        print("\n=== Step 4: Extract candidates [MOCK] ===")
        candidates = MOCK_CANDIDATES
        Path(CANDIDATES_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(CANDIDATES_PATH).write_text(json.dumps(candidates, indent=2), encoding="utf-8")
        print(f"  {len(candidates)} mock candidates written to {CANDIDATES_PATH}")
        return candidates

    chunks = run_dry_run(docx_path)
    print("\n=== Step 4: Extract candidates ===")
    candidates = detect_candidates(chunks, CANDIDATES_PATH)

    print("\n=== Step 4b: Deduplicate candidates ===")
    pre_count = len(candidates)
    candidates = deduplicate_candidates(candidates, threshold=_DEDUP_THRESHOLD)
    post_count = len(candidates)
    print(f"  {pre_count} -> {post_count} candidates after dedup (threshold={_DEDUP_THRESHOLD})")

    if post_count > _MAX_CANDIDATES:
        print(f"[warning] {post_count} candidates exceed MAX_CANDIDATES_PER_SESSION={_MAX_CANDIDATES}; "
              f"excess will be routed to Triage")
        # Tag lowest-confidence excess candidates for triage routing
        conf_order = {"Low": 0, "Medium": 1, "High": 2}
        sorted_candidates = sorted(candidates, key=lambda c: conf_order.get(c.get("confidence", "Medium"), 1))
        for c in sorted_candidates[:post_count - _MAX_CANDIDATES]:
            c["_triage_reason"] = "exceeds_session_cap"

    # Persist deduped candidates
    Path(CANDIDATES_PATH).write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    return candidates


def _split_rows(rows: list[dict], include_low_confidence: bool = False) -> tuple[list[dict], list[dict]]:
    """
    Split classified rows into (primary_rows, triage_rows).

    primary_rows  — Medium/High confidence + not tagged with _triage_reason
    triage_rows   — Low confidence OR tagged with _triage_reason (session cap excess)

    When include_low_confidence=True all rows go to primary_rows.
    """
    if include_low_confidence:
        return rows, []
    primary, triage = [], []
    for r in rows:
        if r.get("_triage_reason") or r.get("ConfidenceLevel") == "Low":
            triage.append(r)
        else:
            primary.append(r)
    return primary, triage


def run_classify(docx_path: str, mock: bool = False) -> list[dict]:
    if mock:
        print("\n=== Step 5: Classify candidates [MOCK] ===")
        classified = MOCK_CLASSIFIED_ROWS
        print("\n=== Step 5b: Validate rows ===")
        validated = validate_all_rows(classified)
        Path(CLASSIFIED_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(CLASSIFIED_PATH).write_text(json.dumps(validated, indent=2), encoding="utf-8")
        return validated

    # Allow resuming from existing chunks/candidates if available
    if Path(CANDIDATES_PATH).exists():
        print(f"[main] Using existing {CANDIDATES_PATH}")
        candidates = json.loads(Path(CANDIDATES_PATH).read_text(encoding="utf-8"))
    else:
        candidates = run_extract(docx_path)

    print("\n=== Step 5: Classify candidates ===")
    classified = classify_candidates(candidates, CLASSIFIED_PATH)

    print("\n=== Step 5b: Validate rows ===")
    validated = validate_all_rows(classified)

    # Re-save with validation metadata
    Path(CLASSIFIED_PATH).write_text(json.dumps(validated, indent=2), encoding="utf-8")
    return validated


def run_payload(docx_path: str, mock: bool = False, include_low_confidence: bool = False) -> list[dict]:
    if mock:
        rows = run_classify(docx_path, mock=True)
    elif Path(CLASSIFIED_PATH).exists():
        print(f"[main] Using existing {CLASSIFIED_PATH}")
        rows = json.loads(Path(CLASSIFIED_PATH).read_text(encoding="utf-8"))
    else:
        rows = run_classify(docx_path)

    print("\n=== Step 5c: Confidence floor filter ===")
    primary_rows, triage_rows = _split_rows(rows, include_low_confidence)
    if triage_rows:
        print(f"  {len(primary_rows)} primary rows, {len(triage_rows)} routed to Triage "
              f"(low confidence or session cap excess)")
    else:
        print(f"  {len(primary_rows)} rows — no triage rows")

    print("\n=== Step 6: Export review workbook ===")
    export_review_workbook(primary_rows, REVIEW_PATH, triage_rows=triage_rows)

    print("\n=== Step 7: Build SharePoint payload ===")
    build_sharepoint_payload(primary_rows, PAYLOAD_PATH)

    print("\n=== Step 8: Generate HTML report ===")
    generate_report(CLASSIFIED_PATH, str(Path("output") / "ai_opportunity_report.html"),
                    triage_rows=triage_rows)
    return primary_rows, triage_rows


def run_push(docx_path: str, mock: bool = False, include_low_confidence: bool = False) -> None:
    run_payload(docx_path, mock=mock, include_low_confidence=include_low_confidence)
    payload = json.loads(Path(PAYLOAD_PATH).read_text(encoding="utf-8"))

    print("\n=== Step 8: Push to Power Automate ===")
    push_to_power_automate(payload)


def rebuild_all_reports(history: list[dict]) -> None:
    """
    Regenerate every archived weekly report and every monthly report from the
    current history.  Called automatically when a back-dated transcript is ingested
    so that all downstream reports stay longitudinally accurate.

    For weekly reports, uses the archived classified_rows.json (if present) so the
    Cards / Analytics / Table tabs show exactly that week's rows.  Falls back to
    the history snapshots for that date when the archive file is missing.
    """
    from trend_analyzer import all_dates

    dates = all_dates(history)
    months = sorted({d[:7] for d in dates})   # "YYYY-MM"

    print(f"\n=== Rebuild: regenerating {len(dates)} weekly + {len(months)} monthly reports ===")

    for d in dates:
        from datetime import datetime as _dt
        meeting_date = _dt.strptime(d, "%Y-%m-%d").date()
        archive_dir = period_utils.week_archive_dir(meeting_date)
        weekly_path = str(archive_dir / "weekly_report.html")
        archived_rows_path = archive_dir / "classified_rows.json"
        week_rows = (
            json.loads(archived_rows_path.read_text(encoding="utf-8"))
            if archived_rows_path.exists()
            else None
        )
        generate_weekly_report(history, meeting_date, weekly_path, week_rows=week_rows)

    for month in months:
        monthly_path = str(period_utils.monthly_report_path(month))
        generate_monthly_report(history, month, monthly_path)
        print(f"[rebuild] monthly {month} -> {monthly_path}")

    print(f"[rebuild] done — {len(dates)} weekly + {len(months)} monthly reports refreshed")

    # Rebuild master opportunities workbook from all archived weeks
    print("[rebuild] refreshing master opportunities workbook ...")
    from master_exporter import update_master as _update_master
    try:
        for d in dates:
            from datetime import datetime as _dt3
            meeting_date_obj = _dt3.strptime(d, "%Y-%m-%d").date()
            archive_dir = period_utils.week_archive_dir(meeting_date_obj)
            archived_rows_path = archive_dir / "classified_rows.json"
            if archived_rows_path.exists():
                week_rows_m = json.loads(archived_rows_path.read_text(encoding="utf-8"))
                _update_master(week_rows_m, d)
    except PermissionError:
        print("  [warning] master_opportunities.xlsx is open in Excel -- close it and re-run to update")

    # Regenerate the upcoming session presentation from the latest meeting date.
    if dates:
        from datetime import datetime as _dt2
        last_date = _dt2.strptime(dates[-1], "%Y-%m-%d").date()
        from presentation_builder import build_meeting_presentation
        last_rows_path = period_utils.week_archive_dir(last_date) / "classified_rows.json"
        last_rows = (
            json.loads(last_rows_path.read_text(encoding="utf-8"))
            if last_rows_path.exists()
            else None
        )
        pres_path = build_meeting_presentation(history, last_date, last_week_rows=last_rows)
        print(f"[rebuild] upcoming presentation -> {pres_path}")


def run_weekly(docx_path: str, mock: bool = False, override_date: str | None = None,
               include_low_confidence: bool = False, push_ado: bool = False,
               skip_review_gate: bool = False) -> None:
    """Process a week's transcript, archive it, ingest into history, build weekly report."""

    # Step 0 — ADO status sync (read-only; silently skipped if ADO_PAT absent)
    try:
        import ado_client
        print("\n=== Step 0: Sync ADO work item statuses ===")
        ado_client.sync_all_weeks()
    except Exception as e:
        print(f"[ado] [WARN] Sync skipped due to error: {e}")

    # Always clear stale intermediate cache so a new transcript is never contaminated
    # by artifacts from a previous run.
    for stale in (CHUNKS_PATH, CANDIDATES_PATH, CLASSIFIED_PATH):
        if Path(stale).exists():
            Path(stale).unlink()
            print(f"[main] cleared stale cache: {stale}")

    primary_rows, triage_rows = run_payload(docx_path, mock=mock,
                                             include_low_confidence=include_low_confidence)

    meeting_date = period_utils.resolve_meeting_date(docx_path or "", override_date)
    period = period_utils.period_info(meeting_date)

    # Step 5d — build review queue (idempotent: preserves existing approvals on re-run)
    import review_queue as rq
    rq.build_queue_from_rows(primary_rows, period["date"])
    pending_count = sum(
        1 for it in rq.load_queue(period["date"]) if it.get("status") == "pending"
    )
    print(f"\n=== Step 5d: Review queue ===")
    print(f"  {pending_count} item(s) pending review -> output/review_queue/{period['date']}/queue.json")
    if pending_count > 0:
        print(f"  Run: python src/main.py --mode review --date {period['date']}")
        if push_ado and not skip_review_gate:
            print(f"  [ado] NOTE: --push-ado requires approved items. Review before pushing.")
    print(f"\n=== Step 9: Archive week {period['date']} ({period['week']}) ===")
    period_utils.ensure_dirs()
    archive_dir = period_utils.week_archive_dir(meeting_date)
    archive_dir.mkdir(parents=True, exist_ok=True)
    for src in (CLASSIFIED_PATH, REVIEW_PATH, PAYLOAD_PATH):
        if Path(src).exists():
            shutil.copy2(src, archive_dir / Path(src).name)
    print(f"  archived classified rows, workbook, payload -> {archive_dir}")

    print("\n=== Step 9b: Update master opportunities workbook ===")
    try:
        update_master(primary_rows, period["date"])
    except PermissionError:
        print("  [warning] master_opportunities.xlsx is open in Excel -- close it and re-run to update")

    if push_ado:
        print("\n=== Step 9c: Push new opportunities to ADO ===")
        try:
            import ado_client
            if ado_client.is_configured():
                # ── Review gate ───────────────────────────────────────────────
                if skip_review_gate:
                    print("[ado] WARNING: --skip-review-gate is set -- pushing unreviewed opportunities")
                    rows_to_push = [r for r in primary_rows if not r.get("ADOWorkItemId")]
                else:
                    all_rows_count = len([r for r in primary_rows if not r.get("ADOWorkItemId")])
                    rows_to_push = [
                        r for r in primary_rows
                        if r.get("review_status") == "approved" and not r.get("ADOWorkItemId")
                    ]
                    skipped_count = all_rows_count - len(rows_to_push)
                    if skipped_count > 0:
                        print(f"[ado] {skipped_count} row(s) skipped -- not yet approved by reviewer")
                        print(f"[ado] Run --mode review --date {period['date']} to approve items first")
                    if not rows_to_push:
                        print("[ado] No approved rows to push. Skipping ADO push.")
                        rows_to_push = []

                if rows_to_push:
                    epic_id = ado_client.get_or_create_epic()
                    if epic_id > 0:
                        updated_rows = []
                        for row in rows_to_push:
                            updated_rows.append(ado_client.push_work_item(row, epic_id))
                        # Write ADO fields back to the archived classified_rows.json
                        archived_classified = archive_dir / "classified_rows.json"
                        if archived_classified.exists():
                            existing = json.loads(archived_classified.read_text(encoding="utf-8"))
                            id_to_ado = {r.get("Title"): r for r in updated_rows}
                            for row in existing:
                                pushed = id_to_ado.get(row.get("Title"))
                                if pushed and pushed.get("ADOWorkItemId"):
                                    row["ADOWorkItemId"] = pushed["ADOWorkItemId"]
                                    row["ADOUrl"]        = pushed["ADOUrl"]
                                    row["ADOStatus"]     = pushed["ADOStatus"]
                                    row["ADOPushedAt"]   = pushed["ADOPushedAt"]
                            archived_classified.write_text(
                                json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
                            )
            else:
                print("[ado] Skipping push — ADO_PAT not configured")
        except Exception as e:
            print(f"[ado] [WARN] Push skipped due to error: {e}")

    print("\n=== Step 10: Ingest into opportunity history ===")
    # Snapshot the existing maximum date BEFORE ingest to detect back-dating.
    history_before = load_history()
    existing_dates = sorted(
        {o["date"] for e in history_before for o in e.get("occurrences", [])}
    )
    max_existing_date = existing_dates[-1] if existing_dates else None

    history = ingest_week(primary_rows, meeting_date)
    print(f"  history now tracks {len(history)} unique opportunities")

    # If the new transcript is earlier than (or equal to) the latest existing week,
    # every subsequent weekly report and all monthly reports are now stale — rebuild all.
    is_backdated = max_existing_date is not None and period["date"] <= max_existing_date
    if is_backdated:
        print(f"\n  Back-dated transcript detected ({period['date']} <= existing max {max_existing_date})")
        print("  Rebuilding ALL weekly and monthly reports for longitudinal accuracy ...")
        rebuild_all_reports(history)
    else:
        print("\n=== Step 11: Generate weekly trend report ===")
        weekly_path = str(archive_dir / "weekly_report.html")
        generate_weekly_report(history, meeting_date, weekly_path,
                               week_rows=primary_rows, triage_rows=triage_rows)

        # Also build the rolling monthly report so it stays current.
        monthly_path = str(period_utils.monthly_report_path(period["month"]))
        generate_monthly_report(history, period["month"], monthly_path)

    print(f"\n[done] Weekly report: {archive_dir / 'weekly_report.html'}")
    print(f"[done] Monthly report: {period_utils.monthly_report_path(period['month'])}")

    print("\n=== Step 12: Generate upcoming meeting presentation ===")
    from presentation_builder import build_meeting_presentation
    pres_path = build_meeting_presentation(history, meeting_date, last_week_rows=primary_rows)
    print(f"[done] Meeting presentation: {pres_path}")


def run_monthly(docx_path: str | None, override_date: str | None, month: str | None) -> None:
    """Build the monthly trend report from accumulated history."""
    history = load_history()
    if not history:
        print("[error] No history found. Run --mode weekly on at least one transcript first.")
        sys.exit(1)

    if month is None:
        if docx_path:
            meeting_date = period_utils.resolve_meeting_date(docx_path, override_date)
        elif override_date:
            from datetime import datetime
            meeting_date = datetime.strptime(override_date, "%Y-%m-%d").date()
        else:
            # Default to the most recent month present in history.
            month = max(o["month"] for e in history for o in e["occurrences"])
        if month is None:
            month = period_utils.month_label(meeting_date)

    print(f"\n=== Build monthly trend report for {month} ===")
    period_utils.ensure_dirs()
    monthly_path = str(period_utils.monthly_report_path(month))
    generate_monthly_report(history, month, monthly_path)
    print(f"\n[done] Monthly report: {monthly_path}")


# ── Review mode ───────────────────────────────────────────────────────────────

def _get_reviewer_id() -> str:
    """Return reviewer ID from env or os.getlogin()."""
    rid = os.getenv("REVIEWER_ID", "").strip()
    if rid:
        return rid
    try:
        return os.getlogin()
    except Exception:
        return "unknown"


def run_review(date: str | None) -> None:
    """
    Interactive CLI review queue.

    Walks through pending items for the given date (or the most recent archived
    week if date is omitted), presenting each opportunity's key fields and
    asking the reviewer to Approve / Reject / Edit / Keep pending / Quit.
    """
    import review_queue as rq
    from schema_migrations import migrate_list

    # Resolve date
    if date is None:
        weeks = sorted(Path("output/weeks").glob("*/classified_rows.json"))
        if not weeks:
            print("[review] No archived weeks found. Run --mode weekly first.")
            return
        date = weeks[-1].parent.name
        print(f"[review] No --date specified; using most recent week: {date}")

    archive_path = Path("output") / "weeks" / date / "classified_rows.json"
    if not archive_path.exists():
        print(f"[review] No archived classified rows found at {archive_path}")
        return

    rows: list[dict] = migrate_list(
        json.loads(archive_path.read_text(encoding="utf-8"))
    )
    items = rq.build_queue_from_rows(rows, date)
    pending = rq.get_pending(items)

    if not pending:
        approved = sum(1 for it in items if it.get("status") == "approved")
        rejected = sum(1 for it in items if it.get("status") == "rejected")
        print(f"[review] All {len(items)} items already reviewed for {date}.")
        print(f"  Approved: {approved}  Rejected: {rejected}")
        return

    reviewer_id = _get_reviewer_id()
    print(f"\n[review] Reviewer: {reviewer_id}")
    print(f"[review] Week: {date}  |  {len(pending)} of {len(items)} items pending review")
    print("─" * 72)

    actions_taken = {"approved": 0, "rejected": 0, "edited": 0, "skipped": 0}
    id_to_item = {it["id"]: it for it in items}

    for item in pending:
        # Find the matching row for display
        row = next(
            (r for r in rows if rq._slugify(r.get("Title", "")) == item["id"]),
            {}
        )
        print(f"\n  TITLE:          {row.get('Title', item['id'])}")
        print(f"  TYPE:           {row.get('AIUseCaseType', '?')}  |  CONFIDENCE: {row.get('ConfidenceLevel', '?')}")
        print(f"  MATURITY:       {row.get('MaturitySignal', '?')}  |  PRIORITY: {row.get('Priority', '?')}")
        print(f"  BUCKET:         {row.get('OperatingBucket', '?')}")
        print(f"  LEVEL:          {row.get('LevelOfAnalysis', '?')}")
        print(f"  PROCESS STAGE:  {row.get('ProcessStage', '?')}")
        print(f"  SUB. FUNCTION:  {row.get('SubOrdinateFunction', '?')}")
        print(f"  TOOL:           {row.get('PrimaryTool', '?')}")
        print(f"  OWNER / SME:    {row.get('SuggestedBusinessOwnerText', '?')}  /  {row.get('SuggestedSMEChampionText', '?')}")
        print(f"  EVIDENCE:       {str(row.get('EvidenceSummary', ''))[:120]}")
        print(f"  PROBLEM:        {str(row.get('ProblemPainPoint', ''))[:120]}")
        print()

        while True:
            choice = input("  [A]pprove / [R]eject / [E]dit field / [K]eep pending / [Q]uit: ").strip().upper()

            if choice == "A":
                notes = input("  Notes (optional, Enter to skip): ").strip()
                rq.action_approve(item, reviewer_id, notes=notes, date=date)
                id_to_item[item["id"]] = item
                actions_taken["approved"] += 1
                print(f"  ✓ Approved")
                break

            elif choice == "R":
                reason = input("  Reason for rejection (required): ").strip()
                if not reason:
                    print("  [review] Rejection reason is required.")
                    continue
                rq.action_reject(item, reviewer_id, reason=reason, date=date)
                id_to_item[item["id"]] = item
                actions_taken["rejected"] += 1
                print(f"  ✗ Rejected")
                break

            elif choice == "E":
                _EDITABLE_FIELDS = [
                    ("Title",                      "Title"),
                    ("AIUseCaseType",               "Type"),
                    ("ConfidenceLevel",             "Confidence"),
                    ("Priority",                    "Priority"),
                    ("MaturitySignal",              "Maturity Signal"),
                    ("OperatingBucket",             "Bucket"),
                    ("LevelOfAnalysis",             "Level"),
                    ("ProcessStage",                "Process Stage"),
                    ("SubOrdinateFunction",         "Sub. Function"),
                    ("PrimaryTool",                 "Tool"),
                    ("SuggestedBusinessOwnerText",  "Owner"),
                    ("SuggestedSMEChampionText",    "SME Champion"),
                    ("ProblemPainPoint",            "Problem / Pain Point"),
                    ("EvidenceSummary",             "Evidence Summary"),
                    ("NextStep",                    "Next Step"),
                ]
                print()
                for idx, (fname, label) in enumerate(_EDITABLE_FIELDS, 1):
                    print(f"    {idx:>2}.  {label:<30}  {row.get(fname, '')}")
                print()
                sel = input("  Edit field number (or type field name): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(_EDITABLE_FIELDS):
                    field = _EDITABLE_FIELDS[int(sel) - 1][0]
                else:
                    field = sel
                if field not in row:
                    print(f"  [review] Unknown field '{field}'.")
                    continue
                current = row.get(field)
                print(f"  Current value: {current}")
                new_val = input("  New value: ").strip()
                notes = input("  Notes (optional): ").strip()
                result = rq.action_edit(
                    item, reviewer_id, field, new_val,
                    notes=notes, date=date,
                    model_value=row.get("_model", {}).get(field, current),
                )
                if result is None:
                    continue  # validation failed — re-prompt
                row[field] = new_val
                id_to_item[item["id"]] = item
                actions_taken["edited"] += 1
                print(f"  ✎ Field '{field}' updated to '{new_val}'")
                # Ask if they want to approve after editing
                cont = input("  Approve now? [Y/N]: ").strip().upper()
                if cont == "Y":
                    approve_notes = input("  Notes (optional): ").strip()
                    rq.action_approve(item, reviewer_id, notes=approve_notes, date=date)
                    id_to_item[item["id"]] = item
                    actions_taken["approved"] += 1
                    print(f"  ✓ Approved")
                break

            elif choice == "K":
                actions_taken["skipped"] += 1
                print(f"  -> Kept pending")
                break

            elif choice == "Q":
                print("\n[review] Session ended by reviewer.")
                break
            else:
                print("  Enter A, R, E, K, or Q.")
                continue

        if choice == "Q":
            break

    # Save updated queue
    rq.save_queue(date, list(id_to_item.values()))

    # Write review fields back to archived classified_rows.json
    updated_rows = rq.apply_queue_to_rows(rows, list(id_to_item.values()))
    archive_path.write_text(
        json.dumps(updated_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n─" * 72)
    print(f"[review] Session summary for {date}:")
    print(f"  Approved : {actions_taken['approved']}")
    print(f"  Rejected : {actions_taken['rejected']}")
    print(f"  Edited   : {actions_taken['edited']}")
    print(f"  Skipped  : {actions_taken['skipped']}")
    remaining = sum(1 for it in id_to_item.values() if it.get("status") == "pending")
    print(f"  Still pending: {remaining}")
    if remaining > 0:
        print(f"\n  Run --mode review --date {date} again to continue.")
    print(f"\n  Feedback records written to: {Path('output/feedback/feedback_log.jsonl')}")


# ── Apply-feedback mode ───────────────────────────────────────────────────────

def run_apply_feedback(version: str | None) -> None:
    """Convert accumulated feedback log into staged prompt proposals."""
    from feedback_applier import build_staged_version
    import feedback_store

    records = feedback_store.load_all()
    if not records:
        print("[feedback] No feedback records found. Run --mode review first.")
        return

    edits = [r for r in records if r.get("event") == "field_edit"]
    approvals = [r for r in records if r.get("event") == "approve"]
    rejections = [r for r in records if r.get("event") == "reject"]

    print(f"[feedback] {len(records)} total records — "
          f"{len(edits)} edits, {len(approvals)} approvals, {len(rejections)} rejections")

    staging_dir = build_staged_version(version, records)
    print(f"[feedback] Staged version written to: {staging_dir}")
    print(f"\nNext steps:")
    print(f"  1. Review the staged files in {staging_dir}")
    print(f"  2. Run --mode eval to check classifier accuracy")
    print(f"  3. Run --mode promote-feedback --feedback-version <version> if eval passes")


# ── Eval mode ─────────────────────────────────────────────────────────────────

def run_eval() -> None:
    """Run the classifier against the labelled eval set and report accuracy."""
    from evaluator import load_examples, run_eval as _run_eval, write_eval_report

    examples = load_examples()
    if not examples:
        print("[eval] No examples found in config/eval/examples.jsonl")
        print("  Run --mode apply-feedback then --mode promote-feedback to seed examples.")
        return

    if len(examples) < 5:
        print(f"[eval] Only {len(examples)} examples found — minimum 5 required for a meaningful eval.")
        print("  Accumulate more reviewer feedback before running eval.")
        return

    print(f"[eval] Running classifier against {len(examples)} labelled examples...")
    results = _run_eval(examples)
    report_path = write_eval_report(results)

    print(f"\n[eval] Overall accuracy: {results['overall_accuracy']:.1%}  "
          f"({'PASS' if results['pass'] else 'FAIL'} — threshold {results['threshold']:.0%})")
    print("\nPer-field accuracy:")
    for field, acc in sorted(results.get("per_field_accuracy", {}).items(),
                             key=lambda x: x[1]):
        bar = "#" * int(acc * 20)
        print(f"  {field:<35} {acc:5.1%}  [{bar:<20}]")
    print(f"\n[eval] Report written to: {report_path}")


# ── Promote-feedback mode ─────────────────────────────────────────────────────

def run_promote_feedback(version: str) -> None:
    """Apply staged feedback version to classifier — only if eval passes."""
    from feedback_applier import promote_version

    print(f"[promote] Promoting staged version: {version}")
    promote_version(version)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Transcript Intake Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        required=False,
        help="Path to the .docx transcript file (optional for --mode monthly with --month)",
    )
    parser.add_argument(
        "--mode", "-m",
        required=True,
        choices=MODES,
        help="Pipeline mode to run",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock candidates/classified rows instead of calling OpenAI (for testing)",
    )
    parser.add_argument(
        "--date",
        help="Override the meeting date (YYYY-MM-DD). Defaults to date parsed from filename.",
    )
    parser.add_argument(
        "--month",
        help="Target month for --mode monthly (YYYY-MM). Defaults to most recent in history.",
    )
    parser.add_argument(
        "--include-low-confidence",
        action="store_true",
        dest="include_low_confidence",
        help="Include Low-confidence rows on all primary surfaces (overrides confidence floor filter)",
    )
    parser.add_argument(
        "--push-ado",
        action="store_true",
        dest="push_ado",
        help="Push newly classified primary rows to ADO as Issues after archiving (requires ADO_PAT in .env)",
    )
    parser.add_argument(
        "--skip-review-gate",
        action="store_true",
        dest="skip_review_gate",
        help="Bypass the review approval gate when using --push-ado (pushes all rows; emits warning)",
    )
    parser.add_argument(
        "--feedback-version",
        dest="feedback_version",
        help="Staged feedback version to promote (for --mode promote-feedback)",
    )
    args = parser.parse_args()

    needs_input = args.mode not in ("monthly", "rebuild", "review",
                                     "apply-feedback", "eval", "promote-feedback")
    if needs_input and not args.input:
        print(f"[error] --input is required for --mode {args.mode}")
        sys.exit(1)
    if args.input and not Path(args.input).exists():
        print(f"[error] Transcript not found: {args.input}")
        sys.exit(1)

    label = args.input or (args.month or "history")
    print(f"\n[main] Mode: {args.mode} | Input: {label}{' | MOCK' if args.mock else ''}")

    match args.mode:
        case "dry-run":
            run_dry_run(args.input)
            print(f"\n[done] Chunks written to {CHUNKS_PATH}")
        case "extract":
            run_extract(args.input, mock=args.mock)
            print(f"\n[done] Candidates written to {CANDIDATES_PATH}")
        case "classify":
            run_classify(args.input, mock=args.mock)
            print(f"\n[done] Classified rows written to {CLASSIFIED_PATH}")
        case "payload":
            run_payload(args.input, mock=args.mock,
                        include_low_confidence=args.include_low_confidence)
            print(f"\n[done] Review workbook: {REVIEW_PATH}")
            print(f"[done] SharePoint payload: {PAYLOAD_PATH}")
            print(f"[done] HTML report: output/ai_opportunity_report.html")
        case "push":
            run_push(args.input, mock=args.mock,
                     include_low_confidence=args.include_low_confidence)
            print("\n[done] Push complete")
        case "weekly":
            run_weekly(args.input, mock=args.mock, override_date=args.date,
                       include_low_confidence=args.include_low_confidence,
                       push_ado=args.push_ado,
                       skip_review_gate=args.skip_review_gate)
        case "monthly":
            run_monthly(args.input, override_date=args.date, month=args.month)
        case "rebuild":
            history = load_history()
            if not history:
                print("[error] No history found. Run --mode weekly on at least one transcript first.")
                sys.exit(1)
            period_utils.ensure_dirs()
            rebuild_all_reports(history)
        case "review":
            run_review(args.date)
        case "apply-feedback":
            run_apply_feedback(args.feedback_version)
        case "eval":
            run_eval()
        case "promote-feedback":
            if not args.feedback_version:
                print("[error] --feedback-version is required for --mode promote-feedback")
                sys.exit(1)
            run_promote_feedback(args.feedback_version)


if __name__ == "__main__":
    main()
