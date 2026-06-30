"""
report_generator.py
Generates a self-contained shareable HTML visualization from classified_rows.json.
Saved to output/ai_opportunity_report.html — no external dependencies required.

Called automatically at end of payload/push modes, or standalone:
  python src/report_generator.py
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter

_ROOT = Path(__file__).parent.parent
_CLASSIFIED = _ROOT / "output" / "classified_rows.json"
_OUTPUT = _ROOT / "output" / "ai_opportunity_report.html"


# ── colour palette ──────────────────────────────────────────────────────────
BUCKET_COLORS = {
    "Cross-Functional/Governance": "#4A6FA5",
    "Crosss-Functional/Governance": "#4A6FA5",
    "Inside/Pre-Sale":               "#47A8BD",
    "Outside/Pre-Sale":              "#5DB7A0",
    "Manufacturing":                 "#E8A838",
    "Post Shipment":                 "#C0604D",
    "Engineering / Product Vitality":"#8E7CC3",
}
TYPE_COLORS = {
    "Classification":  "#47A8BD",
    "Action":          "#E8A838",
    "Both":            "#4A6FA5",
    "Unknown/Needs Review": "#999",
}
SIGNAL_COLORS = {
    "Cross-Functional Pattern":      "#4A6FA5",
    "Repeated Across Multiple Teams":"#47A8BD",
    "Repeated within One Team":      "#E8A838",
    "Isolated Example":              "#bbb",
}
WORKSTREAM_COLORS = {
    "Transactional":   "#4A6FA5",
    "Product Vitality":"#8E7CC3",
    "Governance":      "#47A8BD",
    "Support":         "#5DB7A0",
    "Unknown":         "#6B7280",
}
MATURITY_COLORS = {
    "Delivered / Active Today": "#059669",   # green
    "In Progress / Piloting":   "#2563EB",   # blue
    "Aspirational":             "#D97706",   # amber
    "Unknown":                  "#6B7280",   # gray
}
ADO_STATE_COLORS = {
    # Basic process template states
    "To Do":  "#6B7280",   # gray
    "Doing":  "#2563EB",   # blue
    "Done":   "#059669",   # green
    # Agile/CMMI fallback states (kept for compatibility)
    "New":      "#6B7280",
    "Active":   "#2563EB",
    "Resolved": "#059669",
    "Closed":   "#374151",
}
ADO_STATE_ICONS = {
    # Basic process template states
    "To Do":  "⬜",
    "Doing":  "🔵",
    "Done":   "✅",
    # Agile/CMMI fallback states
    "New":      "⬜",
    "Active":   "🔵",
    "Resolved": "✅",
    "Closed":   "⬛",
}
LEVEL_COLORS = {
    "Level 0 - Signal Capture":          "#e0e0e0",
    "Level 1 - Categorization":          "#b0c4de",
    "Level 2 - Descriptive Analysis":    "#87CEEB",
    "Level 3 - Diagnostic Analysis":     "#4A9ECC",
    "Level 4 - Predictive/Risk Analysis":"#3A7CA5",
    "Level 5 - Prescriptive Recommendation": "#2D5F8A",
    "Level 6 - Action/Automation":   "#1E3F5A",
    "Leve 6 - Action/Automation":        "#1E3F5A",
    "Level 7 - Release Candidate":       "#0A1F2E",
}


def _color_for(mapping: dict, key: str, fallback: str = "#999") -> str:
    return mapping.get(key, fallback)


def _bar_chart_data(rows: list[dict], field: str, color_map: dict) -> dict:
    counts = Counter(r.get(field, "Unknown") for r in rows)
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [_color_for(color_map, l) for l in labels]
    return {"labels": labels, "values": values, "colors": colors}


def _score_avg(rows: list[dict], field: str) -> float:
    vals = [r[field] for r in rows if isinstance(r.get(field), (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else 0


def _build_cards_html(rows: list[dict]) -> str:
    cards = []
    for i, r in enumerate(rows):
        title = r.get("Title", "Untitled")
        problem = r.get("ProblemPainPoint", "")
        evidence = r.get("EvidenceSummary", "")
        speaker = r.get("SourceSpeaker", "")
        ts = r.get("SourceTimestamp", "")
        bucket = r.get("OperatingBucket", "")
        use_type = r.get("AIUseCaseType", "")
        level = r.get("LevelOfAnalysis", "")
        signal = r.get("SignalStrength", "")
        next_step = r.get("NextStep", "")
        owner = r.get("SuggestedBusinessOwnerText", "") or r.get("SuggestedSMEChampionText", "")
        confidence = r.get("ConfidenceLevel", "")
        maturity = r.get("MaturitySignal", "") or "Unknown"
        tool = r.get("PrimaryTool", "")
        stage = r.get("ProcessStage", "")
        sub_fn = r.get("SubOrdinateFunction", "")
        workstream = r.get("WorkstreamType", "")
        value = r.get("ValueScore", "—")
        effort = r.get("EffortScore", "—")
        risk = r.get("RiskScore", "—")
        ado_id     = r.get("ADOWorkItemId")
        ado_url    = r.get("ADOUrl", "")
        ado_status = r.get("ADOStatus") or "New"
        review_status = r.get("review_status")

        bucket_color  = _color_for(BUCKET_COLORS, bucket)
        type_color    = _color_for(TYPE_COLORS, use_type)
        signal_color  = _color_for(SIGNAL_COLORS, signal)
        maturity_color = MATURITY_COLORS.get(maturity, "#6B7280")
        ado_color     = ADO_STATE_COLORS.get(ado_status, "#6B7280")
        ado_icon      = ADO_STATE_ICONS.get(ado_status, "⬜")

        conf_class = {"High": "conf-high", "Medium": "conf-med", "Low": "conf-low"}.get(confidence, "conf-med")

        ado_chip = ""
        if ado_id:
            ado_chip = (
                f'<a class="ado-chip" href="{ado_url}" target="_blank" rel="noopener" '
                f'style="border-color:{ado_color};color:{ado_color}" title="Open ADO #{ado_id}">'
                f'{ado_icon} ADO #{ado_id} · {ado_status} 🔗</a>'
            )

        # Review status badge
        _REVIEW_BADGE_STYLES = {
            "approved":        ("✓ Approved",       "#155724", "#d4edda", "#c3e6cb"),
            "rejected":        ("✗ Rejected",        "#721c24", "#f8d7da", "#f5c6cb"),
            "needs_reprocess": ("↩ Needs Reprocess", "#856404", "#fff3cd", "#ffeeba"),
            "merged":          ("⇒ Merged",          "#004085", "#cce5ff", "#b8daff"),
        }
        review_badge = ""
        if review_status and review_status in _REVIEW_BADGE_STYLES:
            label, color, bg, border = _REVIEW_BADGE_STYLES[review_status]
            review_badge = (
                f'<span class="review-badge" style="color:{color};background:{bg};'
                f'border:1px solid {border};padding:2px 8px;border-radius:4px;'
                f'font-size:0.75rem;font-weight:600;margin-left:6px">{label}</span>'
            )
        elif not review_status:
            review_badge = (
                '<span class="review-badge" style="color:#6c757d;background:#f8f9fa;'
                'border:1px solid #dee2e6;padding:2px 8px;border-radius:4px;'
                'font-size:0.75rem;margin-left:6px">⏳ Pending Review</span>'
            )

        cards.append(f"""
        <div class="card" data-bucket="{bucket}" data-type="{use_type}" data-workstream="{workstream}" data-signal="{signal}" data-maturity="{maturity}" data-ado-status="{ado_status if ado_id else ''}" data-review-status="{review_status or ''}">
          <div class="card-header" style="border-left: 5px solid {bucket_color};">
            <div class="card-title-row">
              <div class="card-title">{title}</div>
              {ado_chip}
              {review_badge}
            </div>
            <div class="card-badges">
              <span class="badge" style="background:{type_color}">{use_type}</span>
              <span class="badge" style="background:{signal_color}">{signal}</span>
              <span class="badge" style="background:{maturity_color};color:#fff">{maturity}</span>
              <span class="badge {conf_class}">Confidence: {confidence}</span>
            </div>
          </div>
          <div class="card-body">
            <div class="card-section">
              <span class="label">Problem / Pain Point</span>
              <p>{problem}</p>
            </div>
            <div class="card-section">
              <span class="label">Evidence</span>
              <p class="evidence">"{evidence}"</p>
              <span class="source">— {speaker}{(" @ " + ts) if ts else ""}</span>
            </div>
            <div class="card-meta">
              <div class="meta-item"><span class="label">Bucket</span><span>{bucket}</span></div>
              <div class="meta-item"><span class="label">Workstream</span><span>{workstream or "—"}</span></div>
              <div class="meta-item"><span class="label">Level</span><span>{level}</span></div>
              <div class="meta-item"><span class="label">Process Stage</span><span>{stage or "—"}</span></div>
              <div class="meta-item"><span class="label">Sub. Function</span><span>{sub_fn or "—"}</span></div>
              <div class="meta-item"><span class="label">Tool</span><span>{tool}</span></div>
              <div class="meta-item"><span class="label">Owner / SME</span><span>{owner or "TBD"}</span></div>
            </div>
            <div class="card-scores">
              <div class="score-box"><span class="score-val" style="color:#47A8BD">{value}</span><span class="score-lbl">Value</span></div>
              <div class="score-box"><span class="score-val" style="color:#E8A838">{effort}</span><span class="score-lbl">Effort</span></div>
              <div class="score-box"><span class="score-val" style="color:#C0604D">{risk}</span><span class="score-lbl">Risk</span></div>
            </div>
            <div class="card-next">
              <span class="label">Next Step</span>
              <p>{next_step}</p>
            </div>
          </div>
        </div>""")
    return "\n".join(cards)


def _build_table_rows(rows: list[dict]) -> str:
    trs = []
    for r in rows:
        title = r.get("Title", "")
        bucket = r.get("OperatingBucket", "")
        use_type = r.get("AIUseCaseType", "")
        stage = r.get("ProcessStage", "")
        workstream = r.get("WorkstreamType", "")
        level = r.get("LevelOfAnalysis", "")
        signal = r.get("SignalStrength", "")
        tool = r.get("PrimaryTool", "")
        owner = r.get("SuggestedBusinessOwnerText", "") or r.get("SuggestedSMEChampionText", "")
        value = r.get("ValueScore", "")
        effort = r.get("EffortScore", "")
        risk = r.get("RiskScore", "")
        readiness = r.get("ReadinessScore", "")
        confidence = r.get("ConfidenceLevel", "")
        type_color = _color_for(TYPE_COLORS, use_type)
        conf_class = {"High": "conf-high", "Medium": "conf-med", "Low": "conf-low"}.get(confidence, "conf-med")
        trs.append(f"""<tr>
          <td class="td-title">{title}</td>
          <td>{bucket}</td>
          <td><span class="badge" style="background:{type_color};font-size:11px">{use_type}</span></td>
          <td>{stage}</td>
          <td>{workstream or "—"}</td>
          <td>{level}</td>
          <td>{signal}</td>
          <td>{tool}</td>
          <td>{owner or "TBD"}</td>
          <td class="td-score">{value}</td>
          <td class="td-score">{effort}</td>
          <td class="td-score">{risk}</td>
          <td class="td-score">{readiness}</td>
          <td><span class="{conf_class}" style="font-size:11px;font-weight:600">{confidence}</span></td>
        </tr>""")
    return "\n".join(trs)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --blue:   #4A6FA5;
    --teal:   #47A8BD;
    --green:  #5DB7A0;
    --amber:  #E8A838;
    --red:    #C0604D;
    --dark:   #1E2A3A;
    --mid:    #3A4B5C;
    --light:  #F4F7FB;
    --border: #DDE3ED;
    --text:   #2C3E50;
    --muted:  #6B7A8D;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--light); color: var(--text); }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, var(--dark) 0%, var(--mid) 100%);
    color: #fff; padding: 32px 40px 24px;
  }}
  .header-top {{ display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
  .header-sub {{ font-size: 13px; color: rgba(255,255,255,0.65); margin-top: 4px; }}
  .header-meta {{ text-align:right; font-size:12px; color:rgba(255,255,255,0.6); line-height:1.7; }}
  .kpi-row {{ display:flex; gap:16px; margin-top:24px; flex-wrap:wrap; }}
  .kpi {{ background:rgba(255,255,255,0.1); border-radius:10px; padding:14px 20px; min-width:120px; }}
  .kpi-val {{ font-size:28px; font-weight:700; line-height:1; }}
  .kpi-lbl {{ font-size:11px; color:rgba(255,255,255,0.65); margin-top:4px; text-transform:uppercase; letter-spacing:.5px; }}

  /* ── Nav tabs ── */
  .nav {{ background:#fff; border-bottom:2px solid var(--border); display:flex; gap:0; padding: 0 40px; }}
  .nav-tab {{
    padding: 14px 20px; font-size: 13px; font-weight: 600; cursor: pointer;
    color: var(--muted); border-bottom: 3px solid transparent; margin-bottom: -2px;
    transition: color .15s, border-color .15s;
  }}
  .nav-tab:hover {{ color: var(--blue); }}
  .nav-tab.active {{ color: var(--blue); border-bottom-color: var(--blue); }}

  /* ── Sections ── */
  .section {{ display:none; padding: 32px 40px; }}
  .section.active {{ display:block; }}

  /* ── Filters ── */
  .filters {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px; }}
  .filter-btn {{
    padding: 6px 14px; border-radius: 20px; border: 1.5px solid var(--border);
    background: #fff; font-size: 12px; font-weight: 600; cursor: pointer;
    color: var(--muted); transition: all .15s;
  }}
  .filter-btn:hover, .filter-btn.active {{
    background: var(--blue); color: #fff; border-color: var(--blue);
  }}

  /* ── Maturity filter bar ── */
  .maturity-filters {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:24px;
    padding: 10px 14px; background:#F0F4FF; border-radius:10px; border:1px solid #C7D4F0; }}
  .maturity-btn {{
    padding: 5px 14px; border-radius: 20px; border: 1.5px solid transparent;
    font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s;
    background: #fff; color: var(--muted);
  }}
  .maturity-btn.active[data-val="Delivered / Active Today"]  {{ background:#059669; color:#fff; border-color:#059669; }}
  .maturity-btn.active[data-val="In Progress / Piloting"]    {{ background:#2563EB; color:#fff; border-color:#2563EB; }}
  .maturity-btn.active[data-val="Aspirational"]              {{ background:#D97706; color:#fff; border-color:#D97706; }}
  .maturity-btn.active[data-val="Unknown"]                   {{ background:#6B7280; color:#fff; border-color:#6B7280; }}
  .maturity-btn.active {{ background: var(--blue); color:#fff; border-color:var(--blue); }}

  /* ── Cards ── */
  .cards-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap:20px; }}
  .card {{
    background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.07);
    overflow: hidden; transition: box-shadow .2s;
  }}
  .card:hover {{ box-shadow: 0 6px 20px rgba(0,0,0,.12); }}
  .card-header {{ padding: 16px 20px 14px; background: #fafbfd; border-bottom: 1px solid var(--border); }}
  .card-title {{ font-size: 15px; font-weight: 700; color: var(--dark); line-height: 1.3; }}
  .card-title-row {{ display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }}
  .ado-chip {{
    display:inline-flex; align-items:center; gap:4px; white-space:nowrap;
    font-size:11px; font-weight:600; padding:3px 10px; border-radius:20px;
    border:1.5px solid; text-decoration:none; transition:opacity .15s;
    flex-shrink:0;
  }}
  .ado-chip:hover {{ opacity:0.75; }}
  .card-badges {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }}
  .badge {{
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:11px; font-weight:600; color:#fff; white-space:nowrap;
  }}
  .conf-high {{ color: var(--green); }}
  .conf-med  {{ color: var(--amber); }}
  .conf-low  {{ color: var(--red);   }}
  .card-body {{ padding: 16px 20px; }}
  .card-section {{ margin-bottom:14px; }}
  .label {{
    display:block; font-size:10px; font-weight:700; text-transform:uppercase;
    letter-spacing:.6px; color:var(--muted); margin-bottom:4px;
  }}
  .card-section p {{ font-size:13px; line-height:1.55; color:var(--text); }}
  .evidence {{ font-style:italic; color: var(--mid); font-size:13px; line-height:1.5; }}
  .source {{ font-size:11px; color:var(--muted); }}
  .card-meta {{
    display:grid; grid-template-columns:1fr 1fr; gap:10px;
    background:var(--light); border-radius:8px; padding:12px; margin-bottom:12px;
  }}
  .meta-item {{ display:flex; flex-direction:column; gap:2px; }}
  .meta-item span:last-child {{ font-size:12px; font-weight:600; color:var(--dark); }}
  .card-scores {{
    display:flex; gap:12px; margin-bottom:14px;
  }}
  .score-box {{
    flex:1; text-align:center; background:var(--light);
    border-radius:8px; padding:10px 6px;
  }}
  .score-val {{ display:block; font-size:22px; font-weight:700; }}
  .score-lbl {{ display:block; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); margin-top:2px; }}
  .card-next p {{ font-size:13px; color:var(--text); line-height:1.5; }}

  /* ── Charts ── */
  .charts-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(340px,1fr)); gap:24px; }}
  .chart-card {{
    background:#fff; border-radius:12px; padding:24px;
    box-shadow:0 2px 8px rgba(0,0,0,.07);
  }}
  .chart-title {{ font-size:14px; font-weight:700; color:var(--dark); margin-bottom:16px; }}
  .chart-wrap {{ position:relative; height:240px; }}
  .score-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-top:8px; }}
  .score-avg {{
    background:var(--light); border-radius:10px; padding:16px; text-align:center;
  }}
  .score-avg .val {{ font-size:32px; font-weight:700; }}
  .score-avg .lbl {{ font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); margin-top:4px; }}

  /* ── Table ── */
  .table-wrap {{ overflow-x:auto; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.07); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; font-size:12px; }}
  thead tr {{ background:var(--dark); color:#fff; }}
  th {{ padding:12px 14px; text-align:left; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; white-space:nowrap; }}
  td {{ padding:11px 14px; border-bottom:1px solid var(--border); vertical-align:top; }}
  tr:hover td {{ background:#F0F4FA; }}
  .td-title {{ font-weight:600; color:var(--dark); max-width:220px; }}
  .td-score {{ text-align:center; font-weight:700; }}
  table tr:last-child td {{ border-bottom:none; }}

  /* ── Footer ── */
  .footer {{ text-align:center; padding:24px; font-size:11px; color:var(--muted); border-top:1px solid var(--border); background:#fff; margin-top:32px; }}

  @media(max-width:600px) {{
    .header, .section {{ padding: 20px; }}
    .nav {{ padding: 0 16px; }}
    .cards-grid {{ grid-template-columns:1fr; }}
    .charts-grid {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>

<!-- ── Header ── -->
<div class="header">
  <div class="header-top">
    <div>
      <h1>⚡ Electronics AI Working Group</h1>
      <div class="header-sub">{header_sub}</div>
    </div>
    <div class="header-meta">
      Source: Meeting Transcript<br>
      Status: All Needs Review<br>
      Human Review Required
    </div>
  </div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-val">{total_rows}</div><div class="kpi-lbl">Opportunities</div></div>
    <div class="kpi"><div class="kpi-val">{high_signal}</div><div class="kpi-lbl">High Signal</div></div>
    <div class="kpi"><div class="kpi-val">{action_count}</div><div class="kpi-lbl">Action / Both</div></div>
    <div class="kpi"><div class="kpi-val">{avg_value}</div><div class="kpi-lbl">Avg Value Score</div></div>
    <div class="kpi"><div class="kpi-val">{high_conf}</div><div class="kpi-lbl">High Confidence</div></div>
  </div>
</div>

<!-- ── Nav ── -->
<div class="nav">
  <div class="nav-tab active" onclick="showTab('cards')">📋 Opportunity Cards</div>
  <div class="nav-tab" onclick="showTab('charts')">📊 Analytics</div>
  <div class="nav-tab" onclick="showTab('table')">🗂 Full Table</div>
  {extra_nav}
</div>

<!-- ── Cards Tab ── -->
<div id="tab-cards" class="section active">
  <div class="filters" id="card-filters">
    <span style="font-size:12px;font-weight:700;color:var(--muted);align-self:center">Filter:</span>
    <button class="filter-btn active" onclick="filterCards('all', this)">All ({total_rows})</button>
    {bucket_filter_btns}
    {type_filter_btns}
    {workstream_filter_btns}
  </div>
  <div class="maturity-filters" id="maturity-filters">
    <span style="font-size:12px;font-weight:700;color:var(--muted);align-self:center">Maturity:</span>
    <button class="maturity-btn active" onclick="filterMaturity('all', this)">All</button>
    {maturity_filter_btns}
  </div>
  <div class="cards-grid" id="cards-grid">
    {cards_html}
  </div>
</div>

<!-- ── Charts Tab ── -->
<div id="tab-charts" class="section">
  <div class="charts-grid">

    <div class="chart-card">
      <div class="chart-title">By Operating Bucket</div>
      <div class="chart-wrap"><canvas id="chartBucket"></canvas></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">By AI Use Case Type</div>
      <div class="chart-wrap"><canvas id="chartType"></canvas></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">By Workstream Type</div>
      <div class="chart-wrap"><canvas id="chartWorkstream"></canvas></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">By Signal Strength</div>
      <div class="chart-wrap"><canvas id="chartSignal"></canvas></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">By Maturity Signal</div>
      <div class="chart-wrap"><canvas id="chartMaturity"></canvas></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">By Level of Analysis</div>
      <div class="chart-wrap"><canvas id="chartLevel"></canvas></div>
    </div>

    <div class="chart-card" style="grid-column:span 2">
      <div class="chart-title">Average Scores</div>
      <div class="score-grid">
        <div class="score-avg"><div class="val" style="color:var(--teal)">{avg_value}</div><div class="lbl">Value Score</div></div>
        <div class="score-avg"><div class="val" style="color:var(--amber)">{avg_effort}</div><div class="lbl">Effort Score</div></div>
        <div class="score-avg"><div class="val" style="color:var(--red)">{avg_risk}</div><div class="lbl">Risk Score</div></div>
        <div class="score-avg"><div class="val" style="color:var(--blue)">{avg_readiness}</div><div class="lbl">Readiness Score</div></div>
      </div>
    </div>

  </div>
</div>

<!-- ── Table Tab ── -->
<div id="tab-table" class="section">
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Title</th><th>Bucket</th><th>Type</th><th>Process Stage</th><th>Workstream</th>
          <th>Level</th><th>Signal</th><th>Tool</th><th>Owner / SME</th>
          <th>Val</th><th>Eff</th><th>Risk</th><th>Ready</th><th>Conf</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
</div>

{extra_sections}

<div class="footer">
  Electronics AI Working Group · AI Opportunity Intake · Draft — All rows require human review before SharePoint promotion · Generated {generated_date}
</div>

<script>
// ── Tab nav ──────────────────────────────────────────────────────────────────
function showTab(name) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}

// ── Card filter ──────────────────────────────────────────────────────────────
let _activeMaturity = 'all';
let _activeFilter = 'all';

function _applyFilters() {{
  document.querySelectorAll('#cards-grid .card').forEach(card => {{
    const matchFilter = _activeFilter === 'all' ||
      card.dataset.bucket === _activeFilter ||
      card.dataset.type === _activeFilter ||
      card.dataset.workstream === _activeFilter ||
      card.dataset.signal === _activeFilter;
    const matchMaturity = _activeMaturity === 'all' ||
      card.dataset.maturity === _activeMaturity;
    card.style.display = (matchFilter && matchMaturity) ? '' : 'none';
  }});
}}

function filterCards(value, btn) {{
  document.querySelectorAll('#card-filters .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _activeFilter = value;
  _applyFilters();
}}

function filterMaturity(value, btn) {{
  document.querySelectorAll('#maturity-filters .maturity-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _activeMaturity = value;
  _applyFilters();
}}

// ── Charts ───────────────────────────────────────────────────────────────────
const bucketData   = {bucket_data};
const typeData     = {type_data};
const workstreamData = {workstream_data};
const signalData   = {signal_data};
const levelData    = {level_data};
const maturityData = {maturity_data};

function makeDonut(id, data) {{
  new Chart(document.getElementById(id), {{
    type: 'doughnut',
    data: {{
      labels: data.labels,
      datasets: [{{ data: data.values, backgroundColor: data.colors, borderWidth: 2, borderColor: '#fff' }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }}, padding: 12 }} }}
      }}
    }}
  }});
}}

function makeBar(id, data) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{
      labels: data.labels,
      datasets: [{{ data: data.values, backgroundColor: data.colors, borderRadius: 6, borderSkipped: false }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ color: '#eee' }}, ticks: {{ font: {{ size: 11 }} }} }},
        y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});
}}

makeDonut('chartBucket',   bucketData);
makeDonut('chartType',     typeData);
makeDonut('chartWorkstream', workstreamData);
makeBar('chartSignal',     signalData);
makeBar('chartLevel',      levelData);
makeDonut('chartMaturity', maturityData);
{extra_scripts}
</script>
</body>
</html>
"""


def _build_progress_tab(all_historical_rows: list[dict]) -> str:
    """
    Build the HTML content for the Progress tab.
    Groups all ADO-linked rows by status; highlights items updated within last 7 days.
    """
    ado_rows = [r for r in all_historical_rows if r.get("ADOWorkItemId")]
    if not ado_rows:
        return (
            '<div style="padding:32px;text-align:center;color:var(--muted)">'
            'No items have been pushed to ADO yet.</div>'
        )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    def _parse_dt(s):
        if not s:
            return None
        try:
            s = s.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except Exception:
            return None

    moved   = []
    doing   = []   # "Doing" or "Active"
    todo    = []   # "To Do" or "New"
    done    = []   # "Done" / "Resolved" / "Closed"

    for r in ado_rows:
        last_updated = _parse_dt(r.get("ADOLastUpdated"))
        if last_updated and last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        status  = r.get("ADOStatus") or "To Do"
        is_recent = last_updated and last_updated >= cutoff

        entry = {
            "title":       r.get("Title", "Untitled"),
            "ado_id":      r.get("ADOWorkItemId"),
            "ado_url":     r.get("ADOUrl", "#"),
            "status":      status,
            "assignee":    r.get("ADOAssignedTo") or "Unassigned",
            "iteration":   r.get("ADOIteration") or "—",
            "pushed_at":   r.get("ADOPushedAt", "")[:10],
            "week_date":   r.get("_meeting_date", ""),
            "last_updated": r.get("ADOLastUpdated", "")[:10] if r.get("ADOLastUpdated") else "—",
        }
        if is_recent:
            moved.append(entry)
        if status in ("Doing", "Active"):
            doing.append(entry)
        elif status in ("To Do", "New"):
            todo.append(entry)
        elif status in ("Done", "Resolved", "Closed"):
            done.append(entry)

    def _row(e, show_state=False):
        state_chip = f'<span style="font-size:11px;font-weight:600;color:{ADO_STATE_COLORS.get(e["status"],"#999")}">{ADO_STATE_ICONS.get(e["status"],"⬜")} {e["status"]}</span> &nbsp;' if show_state else ""
        return (
            f'<tr>'
            f'<td><a href="{e["ado_url"]}" target="_blank" rel="noopener" '
            f'style="font-weight:600;color:var(--blue);text-decoration:none">#{e["ado_id"]}</a></td>'
            f'<td>{e["title"]}</td>'
            f'<td>{state_chip}{e["assignee"]}</td>'
            f'<td>{e["iteration"]}</td>'
            f'<td>{e["last_updated"]}</td>'
            f'<td style="font-size:11px;color:var(--muted)">{e["week_date"]}</td>'
            f'</tr>'
        )

    def _section(title, color, rows_list, show_state=False):
        if not rows_list:
            return ""
        header_style = f"color:{color};border-bottom:2px solid {color}"
        trs = "\n".join(_row(e, show_state) for e in rows_list)
        return (
            f'<h3 style="margin:24px 0 12px;font-size:15px;{header_style};padding-bottom:6px">{title} ({len(rows_list)})</h3>'
            f'<div class="table-wrap"><table>'
            f'<thead><tr><th>ADO #</th><th>Title</th><th>Assignee</th><th>Iteration</th><th>Last Updated</th><th>Week Raised</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div>'
        )

    html = '<div style="padding:0">'
    html += _section("🔄 Moved This Week", "#7C3AED", moved, show_state=True)
    html += _section(f"{ADO_STATE_ICONS['Doing']} In Progress (Doing)", ADO_STATE_COLORS["Doing"], doing)
    html += _section(f"{ADO_STATE_ICONS['To Do']} Queued (To Do)", ADO_STATE_COLORS["To Do"], todo)
    html += _section(f"{ADO_STATE_ICONS['Done']} Completed (Done)", ADO_STATE_COLORS["Done"], done)
    html += "</div>"
    return html


def build_progress_tab_injection(all_historical_rows: list[dict]) -> tuple[str, str]:
    """
    Returns (extra_nav, extra_section) strings for injection into build_report_html().
    Pass all rows from all historical weeks (including ADO fields).
    """
    nav = '<div class="nav-tab" onclick="showTab(\'progress\')">🔄 Progress</div>'
    section = (
        f'<div id="tab-progress" class="section">'
        f'{_build_progress_tab(all_historical_rows)}'
        f'</div>'
    )
    return nav, section


def build_report_html(
    rows: list[dict],
    *,
    generated_date: str | None = None,
    report_title: str = "Electronics AI Working Group — Opportunity Report",
    header_sub: str | None = None,
    extra_nav: str = "",
    extra_sections: str = "",
    extra_scripts: str = "",
) -> str:
    """
    Render the canonical Electronics AI opportunity report HTML for `rows`.

    This is the single source of truth for the report layout (KPI header, the
    Opportunity Cards / Analytics / Full Table tabs, filters and Chart.js charts).
    Additional tabs (e.g. a weekly "Trends" tab) are injected via `extra_nav`
    (extra nav-tab buttons), `extra_sections` (extra `.section` blocks) and
    `extra_scripts` (extra JS appended after the built-in chart setup).
    """
    if generated_date is None:
        generated_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    if header_sub is None:
        header_sub = f"AI Opportunity Intake Report · Generated {generated_date}"

    # KPIs
    total_rows = len(rows)
    high_signal = sum(1 for r in rows if r.get("SignalStrength") in
                      ("Cross-Functional Pattern", "Repeated Across Multiple Teams"))
    action_count = sum(1 for r in rows if r.get("AIUseCaseType") in ("Action", "Both"))
    high_conf = sum(1 for r in rows if r.get("ConfidenceLevel") == "High")
    avg_value    = _score_avg(rows, "ValueScore")
    avg_effort   = _score_avg(rows, "EffortScore")
    avg_risk     = _score_avg(rows, "RiskScore")
    avg_readiness= _score_avg(rows, "ReadinessScore")

    # Chart data
    bucket_data  = json.dumps(_bar_chart_data(rows, "OperatingBucket", BUCKET_COLORS))
    type_data    = json.dumps(_bar_chart_data(rows, "AIUseCaseType",   TYPE_COLORS))
    workstream_data = json.dumps(_bar_chart_data(rows, "WorkstreamType", WORKSTREAM_COLORS))
    signal_data  = json.dumps(_bar_chart_data(rows, "SignalStrength",  SIGNAL_COLORS))
    level_data   = json.dumps(_bar_chart_data(rows, "LevelOfAnalysis", LEVEL_COLORS))
    maturity_data = json.dumps(_bar_chart_data(rows, "MaturitySignal", {
        "Delivered / Active Today": "#059669",
        "In Progress / Piloting":   "#2563EB",
        "Aspirational":             "#D97706",
        "Unknown":                  "#6B7280",
    }))

    # Filter buttons
    buckets = sorted({r.get("OperatingBucket", "") for r in rows if r.get("OperatingBucket")})
    types   = sorted({r.get("AIUseCaseType", "")   for r in rows if r.get("AIUseCaseType")})
    workstreams = sorted({r.get("WorkstreamType", "") for r in rows if r.get("WorkstreamType")})
    bucket_btns = " ".join(
        f'<button class="filter-btn" onclick="filterCards(\'{b}\', this)">{b}</button>'
        for b in buckets
    )
    type_btns = " ".join(
        f'<button class="filter-btn" onclick="filterCards(\'{t}\', this)">{t}</button>'
        for t in types
    )
    workstream_btns = " ".join(
        f'<button class="filter-btn" onclick="filterCards(\'{w}\', this)">{w}</button>'
        for w in workstreams
    )

    # Maturity filter buttons (ordered by signal importance, with counts)
    _maturity_order = [
        "Delivered / Active Today", "In Progress / Piloting", "Aspirational", "Unknown"
    ]
    _maturity_color_map = {
        "Delivered / Active Today": "#059669",
        "In Progress / Piloting":   "#2563EB",
        "Aspirational":             "#D97706",
        "Unknown":                  "#6B7280",
    }
    _maturity_counts = {}
    for r in rows:
        m = r.get("MaturitySignal") or "Unknown"
        _maturity_counts[m] = _maturity_counts.get(m, 0) + 1
    maturity_btns = " ".join(
        f'<button class="maturity-btn" data-val="{m}" '
        f'style="border-color:{_maturity_color_map.get(m, "#6B7280")};color:{_maturity_color_map.get(m, "#6B7280")}" '
        f'onclick="filterMaturity(\'{m}\', this)">{m} ({_maturity_counts.get(m, 0)})</button>'
        for m in _maturity_order if _maturity_counts.get(m, 0) > 0
    )

    return HTML_TEMPLATE.format(
        report_title=report_title,
        header_sub=header_sub,
        generated_date=generated_date,
        total_rows=total_rows,
        high_signal=high_signal,
        action_count=action_count,
        high_conf=high_conf,
        avg_value=avg_value,
        avg_effort=avg_effort,
        avg_risk=avg_risk,
        avg_readiness=avg_readiness,
        bucket_data=bucket_data,
        type_data=type_data,
        workstream_data=workstream_data,
        signal_data=signal_data,
        level_data=level_data,
        maturity_data=maturity_data,
        bucket_filter_btns=bucket_btns,
        type_filter_btns=type_btns,
        workstream_filter_btns=workstream_btns,
        maturity_filter_btns=maturity_btns,
        cards_html=_build_cards_html(rows),
        table_rows=_build_table_rows(rows),
        extra_nav=extra_nav,
        extra_sections=extra_sections,
        extra_scripts=extra_scripts,
    )


def generate_report(
    classified_path: str = str(_CLASSIFIED),
    output_path: str = str(_OUTPUT),
    triage_rows: list[dict] | None = None,
) -> str:
    rows = json.loads(Path(classified_path).read_text(encoding="utf-8"))
    html = build_report_html(rows)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")
    triage_note = f" + {len(triage_rows)} triage" if triage_rows else ""
    print(f"[report] {len(rows)} rows{triage_note} -> {output_path}")
    return output_path


if __name__ == "__main__":
    path = classified_path = str(_CLASSIFIED)
    if len(sys.argv) > 1:
        path = sys.argv[1]
    out = generate_report(classified_path=path)
    print(f"[report] Open in browser: {out}")
