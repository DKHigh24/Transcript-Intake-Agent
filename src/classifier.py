"""
classifier.py
Classifies each extracted candidate into the AI Acceleration MVP schema.
Sends one candidate at a time. Validates against choice_values.json.
Saves output/classified_rows.json.
"""

import copy
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from llm_client import call_llm, llm_backend_name

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_json(filename: str) -> dict | list:
    return json.loads((_CONFIG_DIR / filename).read_text(encoding="utf-8"))


CLASSIFICATION_SYSTEM_PROMPT = """You are an AI opportunity classifier for the Electronics AI Working Group AI Acceleration framework.

Classify a single AI opportunity candidate into the provided JSON schema.

Rules:
- Prefer "Classification" for AIUseCaseType unless the item clearly creates, updates, triggers, sends, automates, or changes a system.
- Use "Both" when the workflow both interprets AND produces output or action.
- Default CurrentStatus to "(2) Needs Review".
- Default HumanReviewRequired and HumanInTheLoopRequired to true.
- Default PrimaryDataSource to "Meeting Transcript".
- Default ScheduleHealth to "Not Started".
- Default DataSensitivity to "Internal".
- Do not invent owners — use SuggestedBusinessOwnerText, SuggestedTechnicalOwnerText, SuggestedSMEChampionText as free text.
- Use only values from the allowed_values object provided.
- Use "Unknown/Needs Review" or leave blank when uncertain.
- Preserve source_speaker, source_timestamp, and evidence_summary from the candidate.
- Set ConfidenceLevel to the candidate's confidence rating.
- Score fields (ValueScore, EffortScore, RiskScore, ReadinessScore, SignalScore) should be integers 1-5.

Return ONLY a valid JSON object matching the schema. No explanation. No markdown fences."""

CLASSIFICATION_USER_TEMPLATE = """Candidate to classify:
{candidate_json}

Target schema (fill every field):
{schema_json}

Allowed values for choice fields:
{choices_json}

Return only the completed JSON object."""


def _call_model(
    candidate: dict,
    schema: dict,
    choices: dict,
) -> dict:
    user_msg = CLASSIFICATION_USER_TEMPLATE.format(
        candidate_json=json.dumps(candidate, indent=2),
        schema_json=json.dumps(schema, indent=2),
        choices_json=json.dumps(choices, indent=2),
    )
    raw = call_llm(CLASSIFICATION_SYSTEM_PROMPT, user_msg)
    return json.loads(raw)


def classify_candidates(
    candidates: list[dict],
    output_path: str = "output/classified_rows.json",
) -> list[dict]:
    """
    Classify each candidate. Returns list of classified row dicts.
    """
    print(f"[classifier] backend: {llm_backend_name()}")
    schema: dict = _load_json("mvp_output_schema.json")
    choices: dict = _load_json("choice_values.json")

    classified: list[dict] = []
    total = len(candidates)

    for i, candidate in enumerate(candidates):
        title = candidate.get("candidate_title", f"Candidate {i+1}")
        print(f"[classifier] {i+1}/{total}: {title}")
        try:
            row = _call_model(candidate, schema, choices)
            # Enforce required defaults in case model drifted
            row.setdefault("CurrentStatus", "(2) Needs Review")
            row.setdefault("HumanReviewRequired", True)
            row.setdefault("HumanInTheLoopRequired", True)
            row.setdefault("PrimaryDataSource", "Meeting Transcript")
            row.setdefault("ScheduleHealth", "Not Started")
            row.setdefault("DataSensitivity", "Internal")
            # Propagate triage tag from candidate (set by session cap guard in main.py)
            if "_triage_reason" in candidate:
                row["_triage_reason"] = candidate["_triage_reason"]
            # Snapshot raw model output and initialise review fields
            row["_model"] = copy.deepcopy({
                k: v for k, v in row.items()
                if not k.startswith("_") and k not in (
                    "review_status", "reviewer_id", "reviewer_timestamp", "reviewer_notes"
                )
            })
            row.setdefault("review_status", None)
            row.setdefault("reviewer_id", None)
            row.setdefault("reviewer_timestamp", None)
            row.setdefault("reviewer_notes", None)
            classified.append(row)
        except Exception as e:
            print(f"  [warn] classification failed for '{title}': {e}")
            # Emit a minimal passthrough row so nothing is silently lost
            classified.append({
                **schema,
                "Title": title,
                "EvidenceSummary": candidate.get("evidence_summary", ""),
                "SourceSpeaker": candidate.get("source_speaker", ""),
                "SourceTimestamp": candidate.get("source_timestamp", ""),
                "ConfidenceLevel": candidate.get("confidence", "Low"),
                "_classification_error": str(e),
            })

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(classified, indent=2), encoding="utf-8")

    print(f"[classifier] {len(classified)} rows classified -> {output_path}")
    return classified
