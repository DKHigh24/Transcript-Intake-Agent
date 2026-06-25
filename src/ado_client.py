"""
ado_client.py — Azure DevOps REST API integration for opportunity push + status sync.

Pushes classified opportunity rows as ADO work items (Issues under a parent Epic).
Reads config from environment variables; never hard-codes credentials.

Public API (called by main.py):
    is_configured()          → bool — True if ADO_PAT + ADO_ORG_URL + ADO_PROJECT are set
    sync_all_weeks()         → int  — sync ADO status across all archived weeks; returns total updated
    get_or_create_epic()     → int  — find or create the parent Epic; returns Epic ID
    push_work_item(row, id)  → dict — push one row, return updated row with ADO fields

CLI (standalone use):
    python src/ado_client.py --test          # push first row from latest classified_rows.json
    python src/ado_client.py --push-all      # push all primary rows from latest classified_rows.json
    python src/ado_client.py --sync          # sync ADO status back into all archived classified_rows.json
"""

import argparse
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ADO_ORG_URL        = os.getenv("ADO_ORG_URL", "").rstrip("/")
ADO_PROJECT        = os.getenv("ADO_PROJECT", "")
ADO_PAT            = os.getenv("ADO_PAT", "")
ADO_WORK_ITEM_TYPE = os.getenv("ADO_WORK_ITEM_TYPE", "Issue")
ADO_AREA_PATH      = os.getenv("ADO_DEFAULT_AREA_PATH", ADO_PROJECT)
ADO_EPIC_TITLE     = os.getenv("ADO_PARENT_EPIC_TITLE", "Electronics AI Working Group Opportunities")

API_VERSION = "7.1"
_WEEKS_DIR  = Path(__file__).parent.parent / "output" / "weeks"
_BATCH_SIZE = 200  # ADO bulk GET limit


# ── Config guards ─────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True only if all required ADO env vars are present."""
    return bool(ADO_PAT and ADO_ORG_URL and ADO_PROJECT)


def _validate_config():
    missing = [k for k, v in {
        "ADO_ORG_URL": ADO_ORG_URL,
        "ADO_PROJECT": ADO_PROJECT,
        "ADO_PAT":     ADO_PAT,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required .env values: {', '.join(missing)}")


# ── Auth ──────────────────────────────────────────────────────────────────────

def _patch_headers() -> dict:
    token = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json-patch+json",
        "Accept":        "application/json",
    }


def _get_headers() -> dict:
    token = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Accept":        "application/json",
    }


# ── Epic management ───────────────────────────────────────────────────────────

def _find_epic(title: str) -> int | None:
    url = f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/wiql?api-version={API_VERSION}"
    query = {
        "query": (
            f"SELECT [System.Id] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{ADO_PROJECT}' "
            f"AND [System.WorkItemType] = 'Epic' "
            f"AND [System.Title] = '{title}' "
            f"AND [System.State] <> 'Closed'"
        )
    }
    resp = requests.post(url, headers=_get_headers(), json=query)
    resp.raise_for_status()
    items = resp.json().get("workItems", [])
    return items[0]["id"] if items else None


def _find_work_item_by_title(title: str) -> dict | None:
    """Return {id, state, url} for the first matching Issue with this title, or None."""
    safe_title = title.replace("'", "''")   # escape single quotes for WIQL
    url = f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/wiql?api-version={API_VERSION}"
    query = {
        "query": (
            f"SELECT [System.Id],[System.State] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{ADO_PROJECT}' "
            f"AND [System.WorkItemType] = '{ADO_WORK_ITEM_TYPE}' "
            f"AND [System.Title] = '{safe_title}' "
            f"AND [System.State] <> 'Removed'"
        )
    }
    try:
        resp = requests.post(url, headers=_get_headers(), json=query)
        resp.raise_for_status()
    except requests.HTTPError:
        return None
    items = resp.json().get("workItems", [])
    if not items:
        return None
    item_id = items[0]["id"]
    detail_url = (
        f"{ADO_ORG_URL}/_apis/wit/workitems/{item_id}?api-version={API_VERSION}"
    )
    try:
        dr = requests.get(detail_url, headers=_get_headers())
        dr.raise_for_status()
        data = dr.json()
        return {
            "id":     item_id,
            "state":  data["fields"].get("System.State", "New"),
            "url":    data["_links"]["html"]["href"],
        }
    except requests.HTTPError:
        return None


def _create_epic(title: str) -> int:
    url = f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/workitems/$Epic?api-version={API_VERSION}"
    body = [
        {"op": "add", "path": "/fields/System.Title",    "value": title},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ADO_AREA_PATH},
        {"op": "add", "path": "/fields/System.Tags",     "value": "AI Working Group; Transcript Intake"},
    ]
    resp = requests.post(url, headers=_patch_headers(), json=body)
    resp.raise_for_status()
    epic_id = resp.json()["id"]
    print(f"[ado] Created Epic #{epic_id}: {title}")
    return epic_id


def get_or_create_epic() -> int:
    """Find or create the parent Epic. Returns Epic ID."""
    if not is_configured():
        print("[ado] Skipping -- ADO_PAT not configured")
        return -1
    epic_id = _find_epic(ADO_EPIC_TITLE)
    if epic_id:
        print(f"[ado] Using existing Epic #{epic_id}: {ADO_EPIC_TITLE}")
        return epic_id
    return _create_epic(ADO_EPIC_TITLE)


# ── Work item push ────────────────────────────────────────────────────────────

def _build_description(row: dict) -> str:
    meeting_date = row.get("_meeting_date", "")
    speaker      = row.get("SourceSpeaker", "")
    timestamp    = row.get("SourceTimestamp", "")
    evidence     = row.get("EvidenceSummary", "")
    problem      = row.get("ProblemPainPoint", "")
    next_step    = row.get("NextStep", "")
    maturity     = row.get("MaturitySignal", "Unknown")
    bucket       = row.get("OperatingBucket", "")
    stage        = row.get("ProcessStage", "")
    sub_fn       = row.get("SubOrdinateFunction", "")
    confidence   = row.get("ConfidenceLevel", "")

    return (
        f"<h3>Problem / Pain Point</h3><p>{problem}</p>"
        f"<h3>Evidence from Meeting</h3>"
        f"<blockquote><em>\"{evidence}\"</em><br/>"
        f"— {speaker}{f' @ {timestamp}' if timestamp else ''}"
        f"{f' · Meeting: {meeting_date}' if meeting_date else ''}</blockquote>"
        f"<h3>Next Step</h3><p>{next_step}</p>"
        f"<hr/><table>"
        f"<tr><td><strong>Maturity Signal</strong></td><td>{maturity}</td></tr>"
        f"<tr><td><strong>Operating Bucket</strong></td><td>{bucket}</td></tr>"
        f"<tr><td><strong>Process Stage</strong></td><td>{stage}</td></tr>"
        f"<tr><td><strong>Sub. Function</strong></td><td>{sub_fn}</td></tr>"
        f"<tr><td><strong>Confidence</strong></td><td>{confidence}</td></tr>"
        f"</table>"
        f"<p><em>Draft — requires human review before action. "
        f"Source: Electronics AI Working Group Transcript Intake Agent.</em></p>"
    )


def push_work_item(row: dict, epic_id: int) -> dict:
    """
    Push one opportunity row as an ADO work item.
    Dedup guards (in order):
      1. row already has ADOWorkItemId → skip (already pushed this session)
      2. ADO already has an Issue with this exact title → recover ID, don't duplicate
      3. Otherwise create a new Issue
    Returns the updated row dict with ADO fields written back.
    """
    if not is_configured():
        print("[ado] Skipping push -- ADO_PAT not configured")
        return row
    if row.get("ADOWorkItemId"):
        return row  # already pushed — skip silently

    title    = row.get("Title", "Untitled Opportunity")

    # Title-based dedup: check if ADO already has this item (e.g., from a prior run)
    existing = _find_work_item_by_title(title)
    if existing:
        row = dict(row)
        row["ADOWorkItemId"] = existing["id"]
        row["ADOUrl"]        = existing["url"]
        row["ADOStatus"]     = existing["state"]
        row["ADOPushedAt"]   = datetime.now(timezone.utc).isoformat()
        print(f"[ado] [SKIP] Recovered existing #{existing['id']}: {title}")
        return row

    maturity = row.get("MaturitySignal", "")
    bucket   = row.get("OperatingBucket", "")
    use_type = row.get("AIUseCaseType", "")
    tags     = "; ".join(filter(None, [
        "AI Working Group", "Transcript Intake",
        maturity, bucket, use_type,
        row.get("ProcessStage", ""),
    ]))

    url = (
        f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/workitems"
        f"/${ADO_WORK_ITEM_TYPE}?api-version={API_VERSION}"
    )
    body = [
        {"op": "add", "path": "/fields/System.Title",       "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": _build_description(row)},
        {"op": "add", "path": "/fields/System.AreaPath",    "value": ADO_AREA_PATH},
        {"op": "add", "path": "/fields/System.Tags",        "value": tags},
        {
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/workItems/{epic_id}",
                "attributes": {"comment": "Parent Epic"},
            },
        },
    ]

    try:
        resp = requests.post(url, headers=_patch_headers(), json=body)
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"[ado] [WARN] Push failed for '{title}': HTTP {e.response.status_code} -- {e.response.text[:200]}")
        return row

    data     = resp.json()
    item_id  = data["id"]
    item_url = data["_links"]["html"]["href"]

    row = dict(row)
    row["ADOWorkItemId"] = item_id
    row["ADOUrl"]        = item_url
    row["ADOStatus"]     = data["fields"].get("System.State", "New")
    row["ADOPushedAt"]   = datetime.now(timezone.utc).isoformat()

    print(f"[ado] Pushed #{item_id}: {title}")
    print(f"[ado]    {item_url}")
    return row


# ── Status sync ───────────────────────────────────────────────────────────────

def _sync_file(classified_path: Path, id_map: dict) -> int:
    """Apply id_map updates to one classified_rows.json. Returns count updated."""
    rows = json.loads(classified_path.read_text(encoding="utf-8"))
    updated = 0
    for row in rows:
        ado_id = row.get("ADOWorkItemId")
        if ado_id and ado_id in id_map:
            fields = id_map[ado_id]
            row["ADOStatus"]      = fields.get("System.State")
            row["ADOIteration"]   = fields.get("System.IterationPath")
            row["ADOAssignedTo"]  = (fields.get("System.AssignedTo") or {}).get("displayName")
            row["ADOLastUpdated"] = fields.get("System.ChangedDate")
            updated += 1
    if updated:
        classified_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return updated


def sync_all_weeks() -> int:
    """
    Pull latest ADO state for all known work items across all archived weeks.
    Issues a single bulk GET per batch of 200 IDs.
    Returns total number of rows updated across all weeks.
    Silently skips if ADO_PAT is not configured.
    """
    if not is_configured():
        print("[ado] Skipping sync -- ADO_PAT not configured")
        return 0

    # Collect all IDs and their source files
    all_ids: list[int] = []
    for week_dir in sorted(_WEEKS_DIR.glob("????-??-??")):
        p = week_dir / "classified_rows.json"
        if not p.exists():
            continue
        rows = json.loads(p.read_text(encoding="utf-8"))
        all_ids.extend(r["ADOWorkItemId"] for r in rows if r.get("ADOWorkItemId"))

    if not all_ids:
        print("[ado] No ADO work items found to sync")
        return 0

    # Deduplicate and batch
    unique_ids = list(dict.fromkeys(all_ids))
    id_map: dict[int, dict] = {}
    for i in range(0, len(unique_ids), _BATCH_SIZE):
        batch = unique_ids[i:i + _BATCH_SIZE]
        url   = (
            f"{ADO_ORG_URL}/_apis/wit/workitems"
            f"?ids={','.join(str(x) for x in batch)}&api-version={API_VERSION}"
        )
        try:
            resp = requests.get(url, headers=_get_headers())
            resp.raise_for_status()
        except requests.HTTPError as e:
            print(f"[ado] [WARN] Sync batch failed: HTTP {e.response.status_code} -- last known state preserved")
            continue
        for item in resp.json().get("value", []):
            id_map[item["id"]] = item["fields"]

    # Write back to each week file
    total_updated = 0
    for week_dir in sorted(_WEEKS_DIR.glob("????-??-??")):
        p = week_dir / "classified_rows.json"
        if p.exists():
            n = _sync_file(p, id_map)
            if n:
                print(f"[ado] Synced {n} item(s) in {week_dir.name}")
            total_updated += n

    print(f"[ado] Sync complete -- {total_updated} total item(s) updated across all weeks")
    return total_updated


# ── CLI (thin wrapper — public API is the functions above) ────────────────────

def _latest_classified_path() -> Path:
    week_dirs = sorted(_WEEKS_DIR.glob("????-??-??"))
    if not week_dirs:
        raise FileNotFoundError(f"No week directories found under {_WEEKS_DIR}")
    return week_dirs[-1] / "classified_rows.json"


def main():
    parser = argparse.ArgumentParser(description="ADO work item push / sync")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test",     action="store_true", help="Push first row as a test item")
    group.add_argument("--push-all", action="store_true", help="Push all primary rows from latest week")
    group.add_argument("--sync",     action="store_true", help="Sync ADO status back into archived rows")
    parser.add_argument("--input",   default=None,        help="Path to classified_rows.json (default: latest week)")
    args = parser.parse_args()

    _validate_config()

    if args.sync:
        sync_all_weeks()
        return

    classified_path = Path(args.input) if args.input else _latest_classified_path()
    rows = json.loads(classified_path.read_text(encoding="utf-8"))
    epic_id = get_or_create_epic()

    rows_to_push = [rows[0]] if args.test else [r for r in rows if not r.get("ADOWorkItemId")]
    print(f"[ado] Pushing {len(rows_to_push)} item(s) to {ADO_ORG_URL}/{ADO_PROJECT}...")

    updated_rows = list(rows)
    push_set = {id(r) for r in rows_to_push}
    for i, row in enumerate(rows):
        if id(row) in push_set:
            updated_rows[i] = push_work_item(row, epic_id)

    classified_path.write_text(json.dumps(updated_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ado] Write-back complete -> {classified_path}")


if __name__ == "__main__":
    main()

