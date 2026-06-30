"""
validators.py
Local validation of classified rows against choice_values.json.
Flags invalid choice values and enforces required defaults.
Does not call the model.
"""

import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent / "config"

# Fields that must match an allowed choice value
CHOICE_FIELDS = [
    "RequestingTeam",
    "CurrentStatus",
    "Priority",
    "OperatingBucket",
    "WorkstreamType",
    "ProcessStage",
    "UpstreamDownstreamImpact",
    "AIUseCaseType",
    "PrimaryFunctionChoice",
    "LevelOfAnalysis",
    "AutomationRisk",
    "SignalStrength",
    "FrequencyOfPainPoint",
    "ManualEffortLevel",
    "Repeatability",
    "ScalabilityPotential",
    "PrimaryTool",
    "PrimaryDataSource",
    "DataSensitivity",
    "ScheduleHealth",
]

REQUIRED_DEFAULTS = {
    "CurrentStatus": "(2) Needs Review",
    "HumanReviewRequired": True,
    "HumanInTheLoopRequired": True,
    "PrimaryDataSource": "Meeting Transcript",
    "ScheduleHealth": "Not Started",
    "DataSensitivity": "Internal",
}

# Normalize common model/doc variants to SharePoint-accepted values.
FIELD_VALUE_ALIASES = {
    "OperatingBucket": {
        "Crosss-Functional/Governance": "Cross-Functional/Governance",
        "Cross-Functional / Governance": "Cross-Functional/Governance",
        "Engineering/Product Vitality": "Engineering / Product Vitality",
        "Engineering / Continuous Improvement": "Engineering / Product Vitality",
        "Product Vitality / Continuous Improvement": "Engineering / Product Vitality",
    },
    "WorkstreamType": {
        "Continuous Improvement": "Product Vitality",
        "Product Vitality / Continuous Improvement": "Product Vitality",
        "Cross-Functional Continuous Improvement": "Product Vitality",
    },
    "AIUseCaseType": {
        "Unknown / Needs Review": "Unknown/Needs Review",
    },
    "LevelOfAnalysis": {
        "Leve 6 - Action/Automation": "Level 6 - Action/Automation",
    },
}


def load_choice_values() -> dict:
    return json.loads((_CONFIG_DIR / "choice_values.json").read_text(encoding="utf-8"))


def validate_row(row: dict, choice_values: dict) -> dict:
    """
    Validate a single classified row.

    Returns a dict with:
        is_valid (bool), warnings (list of str), row (corrected row dict)
    """
    warnings = []
    corrected = dict(row)

    # Enforce required defaults
    for field, default in REQUIRED_DEFAULTS.items():
        if not corrected.get(field):
            corrected[field] = default
            warnings.append(f"'{field}' was missing — defaulted to '{default}'")

    # Validate choice fields
    for field in CHOICE_FIELDS:
        value = corrected.get(field)
        if not value:
            continue

        normalized = FIELD_VALUE_ALIASES.get(field, {}).get(value)
        if normalized:
            corrected[field] = normalized
            warnings.append(f"'{field}' normalized from '{value}' to '{normalized}'")
            value = normalized

        allowed = choice_values.get(field, [])
        if allowed and value not in allowed:
            warnings.append(
                f"'{field}' value '{value}' is not in allowed list. "
                f"Allowed: {allowed}"
            )
            # Fall back to None so reviewers notice it
            corrected[field] = None

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
        "row": corrected,
    }


def validate_all_rows(rows: list[dict]) -> list[dict]:
    """
    Validate all rows. Returns rows with a '_validation' key attached.
    Prints a summary of issues.
    """
    choice_values = load_choice_values()
    validated = []
    total_warnings = 0

    for i, row in enumerate(rows):
        result = validate_row(row, choice_values)
        enriched = dict(result["row"])
        if result["warnings"]:
            enriched["_validation_warnings"] = result["warnings"]
            total_warnings += len(result["warnings"])
            title = row.get("Title", f"Row {i+1}")
            print(f"[validator] '{title}': {len(result['warnings'])} warning(s)")
            for w in result["warnings"]:
                print(f"  - {w}")
        validated.append(enriched)

    print(f"[validator] {len(rows)} rows validated, {total_warnings} total warning(s)")
    return validated
