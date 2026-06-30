"""
distribution_reporter.py
Builds a self-contained HTML report focused on overall distribution (not trends)
across key classification layers for the full opportunity history.

Output default:
    output/reports/overall_distribution.html
"""

import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


_PALETTE = [
    "#4A6FA5", "#47A8BD", "#5DB7A0", "#E8A838", "#C0604D",
    "#8E7CC3", "#6B7A8D", "#2E7D32", "#8D6E63", "#546E7A",
    "#039BE5", "#7CB342",
]


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else ""


def _norm(v) -> str:
    s = str(v).strip() if v is not None else ""
    return s if s else "Unknown"


def _latest_snapshots(history: list[dict]) -> list[dict]:
    latest: list[dict] = []
    for entry in history:
        occ = entry.get("occurrences", [])
        if not occ:
            continue
        latest.append(max(occ, key=lambda o: o.get("date", "")))
    return latest


def _all_snapshots(history: list[dict]) -> list[dict]:
    return [o for e in history for o in e.get("occurrences", [])]


def _count(rows: list[dict], field: str) -> Counter:
    return Counter(_norm(r.get(field)) for r in rows)


def _owner_sme_value(row: dict) -> str:
    owner = _norm(row.get("SuggestedBusinessOwnerText"))
    sme = _norm(row.get("SuggestedSMEChampionText"))
    return f"{owner} | {sme}"


def _count_owner_sme(rows: list[dict]) -> Counter:
    return Counter(_owner_sme_value(r) for r in rows)


def _top(counter: Counter, n: int = 12) -> tuple[list[str], list[int]]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    top_items = items[:n]
    remainder = sum(v for _, v in items[n:])
    if remainder > 0:
        top_items.append(("Other", remainder))
    labels = [k for k, _ in top_items]
    values = [v for _, v in top_items]
    return labels, values


def _chart_block(
    chart_id: str,
    title: str,
    latest_counter: Counter,
    all_counter: Counter,
    top_n: int = 12,
) -> tuple[str, str]:
    latest_labels, latest_vals = _top(latest_counter, top_n)
    all_labels, all_vals = _top(all_counter, top_n)
    label_union = list(dict.fromkeys(latest_labels + all_labels))
    latest_aligned = [latest_counter.get(lbl, 0) for lbl in label_union]
    all_aligned = [all_counter.get(lbl, 0) for lbl in label_union]
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(label_union))]

    section = f"""
    <div class="panel">
      <h3>{_esc(title)}</h3>
      <div class="chart-wrap"><canvas id="{_esc(chart_id)}"></canvas></div>
    </div>"""
    script = f"""
new Chart(document.getElementById('{chart_id}'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(label_union)},
    datasets: [
      {{
        label: 'Current Portfolio (latest snapshot)',
        data: {json.dumps(latest_aligned)},
        backgroundColor: 'rgba(74, 111, 165, 0.85)',
      }},
      {{
        label: 'All Weekly Occurrences (effort exposure)',
        data: {json.dumps(all_aligned)},
        backgroundColor: 'rgba(93, 183, 160, 0.80)',
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {{
      legend: {{ position: 'bottom' }}
    }},
    scales: {{
      x: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}
    }}
  }}
}});"""
    return section, script


def generate_overall_distribution_report(
    history: list[dict],
    out_path: str = "output/reports/overall_distribution.html",
) -> str:
    latest_rows = _latest_snapshots(history)
    all_rows = _all_snapshots(history)
    dates = sorted({o.get("date", "") for o in all_rows if o.get("date")})
    span = f"{dates[0]} to {dates[-1]}" if dates else "No dates"

    layers = [
        ("c_bucket", "Operating Bucket", _count(latest_rows, "OperatingBucket"), _count(all_rows, "OperatingBucket"), 10),
        ("c_workstream", "Workstream Type", _count(latest_rows, "WorkstreamType"), _count(all_rows, "WorkstreamType"), 8),
        ("c_level", "Level of Analysis", _count(latest_rows, "LevelOfAnalysis"), _count(all_rows, "LevelOfAnalysis"), 10),
        ("c_stage", "Process Stage", _count(latest_rows, "ProcessStage"), _count(all_rows, "ProcessStage"), 14),
        ("c_subfn", "Sub Function", _count(latest_rows, "SubOrdinateFunction"), _count(all_rows, "SubOrdinateFunction"), 14),
        ("c_tool", "Primary Tool", _count(latest_rows, "PrimaryTool"), _count(all_rows, "PrimaryTool"), 12),
        ("c_owner", "Owner / SME Pair", _count_owner_sme(latest_rows), _count_owner_sme(all_rows), 14),
    ]

    sections = []
    scripts = []
    for chart_id, title, latest_counter, all_counter, top_n in layers:
        section, script = _chart_block(chart_id, title, latest_counter, all_counter, top_n=top_n)
        sections.append(section)
        scripts.append(script)

    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Overall AI Opportunity Distribution</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:'Segoe UI',system-ui,sans-serif; background:#F4F7FB; color:#2C3E50; }}
    .header {{ background:linear-gradient(135deg,#1E2A3A 0%,#3A4B5C 100%); color:#fff; padding:30px 38px 22px; }}
    .header h1 {{ margin:0 0 6px; font-size:26px; }}
    .header .sub {{ color:#B9C4D1; font-size:14px; }}
    .wrap {{ max-width:1240px; margin:0 auto; padding:24px; }}
    .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-bottom:20px; }}
    .kpi {{ background:#fff; border:1px solid #DDE3ED; border-radius:10px; padding:14px 16px; }}
    .kpi .v {{ font-size:28px; font-weight:700; color:#4A6FA5; }}
    .kpi .l {{ font-size:11px; text-transform:uppercase; color:#6B7A8D; letter-spacing:.04em; margin-top:4px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    .panel {{ background:#fff; border:1px solid #DDE3ED; border-radius:12px; padding:14px 16px; }}
    .panel h3 {{ margin:0 0 8px; font-size:15px; color:#1E2A3A; }}
    .chart-wrap {{ position:relative; height:370px; }}
    .note {{ margin-top:14px; font-size:12px; color:#6B7A8D; }}
    @media (max-width: 1020px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Overall AI Opportunity Distribution</h1>
    <div class="sub">Distribution across the full effort footprint (not trend-only) · Coverage: {_esc(span)}</div>
  </div>
  <div class="wrap">
    <div class="kpis">
      <div class="kpi"><div class="v">{len(history)}</div><div class="l">Unique Opportunities</div></div>
      <div class="kpi"><div class="v">{len(all_rows)}</div><div class="l">Total Weekly Occurrences</div></div>
      <div class="kpi"><div class="v">{len(dates)}</div><div class="l">Weeks Covered</div></div>
      <div class="kpi"><div class="v">{len(latest_rows)}</div><div class="l">Current Portfolio Items</div></div>
    </div>

    <div class="grid">
      {''.join(sections)}
    </div>

    <div class="note">
      Current Portfolio uses each opportunity's latest known snapshot.
      Effort Exposure uses every historical weekly occurrence.
      Generated {generated}.
    </div>
  </div>
  <script>
    {''.join(scripts)}
  </script>
</body>
</html>"""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"[distribution] overall distribution report -> {out}")
    return str(out)
