"""
review_exporter.py
Exports classified and validated rows to output/review_rows.xlsx.
Columns are ordered for human review. Validation warnings appear as a final column.
"""

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# Human-readable column order for review
REVIEW_COLUMNS = [
    "Title",
    "ProblemPainPoint",
    "EvidenceSummary",
    "SourceSpeaker",
    "SourceTimestamp",
    "ConfidenceLevel",           # Column F
    "MaturitySignal",            # Column G
    "AIUseCaseType",
    "PrimaryFunctionChoice",
    "LevelOfAnalysis",
    "OperatingBucket",
    "ProcessStage",              # Column K
    "SubOrdinateFunction",       # Column L
    "UpstreamDownstreamImpact",
    "SignalStrength",
    "RequestingTeam",
    "SuggestedBusinessOwnerText",
    "SuggestedTechnicalOwnerText",
    "SuggestedSMEChampionText",
    "PrimaryTool",
    "PrimaryDataSource",
    "DataSensitivity",
    "AutomationRisk",
    "GuardrailsNeeded",
    "SecurityAccessConcern",
    "LegalComplianceConcern",
    "HumanInTheLoopRequired",
    "HumanReviewRequired",
    "IntegrationNeeded",
    "FrequencyOfPainPoint",
    "ManualEffortLevel",
    "Repeatability",
    "ScalabilityPotential",
    "NextStep",
    "CurrentStatus",
    "Priority",
    "ScheduleHealth",
    "ValueScore",
    "EffortScore",
    "RiskScore",
    "ReadinessScore",
    "SignalScore",
    "_validation_warnings",
]

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
ALT_ROW_FILL = PatternFill("solid", fgColor="EEF2F7")
WARN_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def _format_cell_value(value) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return ""
    return str(value)


def export_review_workbook(
    rows: list[dict],
    output_path: str = "output/review_rows.xlsx",
) -> None:
    """
    Write classified rows to a formatted Excel workbook.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "AI Opportunities"

    # Write header row
    for col_idx, col_name in enumerate(REVIEW_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER

    ws.row_dimensions[1].height = 36

    # Write data rows
    for row_idx, row_data in enumerate(rows, start=2):
        has_warnings = bool(row_data.get("_validation_warnings"))
        for col_idx, col_name in enumerate(REVIEW_COLUMNS, start=1):
            raw = row_data.get(col_name)
            if col_name == "_validation_warnings" and isinstance(raw, list):
                value = " | ".join(raw)
            else:
                value = _format_cell_value(raw)

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = THIN_BORDER
            if col_name == "_validation_warnings" and value:
                cell.fill = WARN_FILL
            elif row_idx % 2 == 0:
                cell.fill = ALT_ROW_FILL

    # Auto-fit column widths (capped)
    for col_idx, col_name in enumerate(REVIEW_COLUMNS, start=1):
        max_len = len(col_name)
        for row_data in rows:
            val = _format_cell_value(row_data.get(col_name))
            max_len = max(max_len, min(len(val), 60))
        ws.column_dimensions[get_column_letter(col_idx)].width = max(12, max_len + 2)

    # Freeze top row
    ws.freeze_panes = "A2"

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    print(f"[exporter] {len(rows)} rows -> {output_path}")
