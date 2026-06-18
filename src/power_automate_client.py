"""
power_automate_client.py
Builds sharepoint_payload.json from classified rows using the field mapping,
and optionally POSTs to a Power Automate HTTP endpoint.

SharePoint push only occurs when:
  - ENABLE_POWER_AUTOMATE_PUSH=true in .env
  - --mode push is passed to main.py
"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

_CONFIG_DIR = Path(__file__).parent.parent / "config"

# Fields that should not be sent in the SharePoint payload
_INTERNAL_FIELDS = {
    "_validation_warnings",
    "_classification_error",
    "SuggestedBusinessOwnerText",
    "SuggestedTechnicalOwnerText",
    "SuggestedSMEChampionText",
    "EvidenceSummary",
    "SourceSpeaker",
    "SourceTimestamp",
    "ConfidenceLevel",
}


def _load_field_mapping() -> dict:
    return json.loads((_CONFIG_DIR / "sharepoint_field_mapping.json").read_text(encoding="utf-8"))


def _map_row_to_fields(row: dict, mapping: dict) -> dict:
    """
    Translate logical field names to SharePoint internal names.
    Skips internal/metadata fields.
    """
    fields = {}
    for logical_name, sp_name in mapping.items():
        if logical_name in _INTERNAL_FIELDS:
            continue
        value = row.get(logical_name)
        if value is None or value == "":
            continue
        fields[sp_name] = value
    return fields


def build_sharepoint_payload(
    rows: list[dict],
    output_path: str = "output/sharepoint_payload.json",
) -> dict:
    """
    Build and save the SharePoint-ready payload JSON.
    """
    mapping = _load_field_mapping()
    sp_rows = []
    for row in rows:
        fields = _map_row_to_fields(row, mapping)
        sp_rows.append({"fields": fields})

    payload = {
        "source": "ai-transcript-intake-agent",
        "mode": "draft-create",
        "rowCount": len(sp_rows),
        "rows": sp_rows,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[payload] {len(sp_rows)} rows -> {output_path}")
    return payload


def push_to_power_automate(payload: dict) -> None:
    """
    POST payload to Power Automate HTTP endpoint.
    Only called when explicitly enabled via env var and --mode push.
    """
    enabled = os.getenv("ENABLE_POWER_AUTOMATE_PUSH", "false").lower() == "true"
    if not enabled:
        print("[push] ENABLE_POWER_AUTOMATE_PUSH is not true — skipping POST.")
        return

    url = os.getenv("POWER_AUTOMATE_URL", "")
    if not url or url.startswith("https://replace"):
        print("[push] POWER_AUTOMATE_URL is not configured — skipping POST.")
        return

    print(f"[push] Posting {payload['rowCount']} row(s) to Power Automate...")
    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    print(f"[push] Response: {response.status_code} — {response.text[:200]}")
