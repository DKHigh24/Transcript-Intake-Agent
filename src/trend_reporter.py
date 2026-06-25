"""
trend_reporter.py
Generates self-contained HTML trend reports from the cumulative opportunity history:

  - generate_weekly_report(history, meeting_date, out_path)
  - generate_monthly_report(history, month, out_path)

Both reports are single-file HTML using Chart.js from CDN and an inline style that
matches the existing ai_opportunity_report.html palette. No external build step.
"""

import html
import json
from datetime import date, datetime
from pathlib import Path

from trend_analyzer import weekly_analysis, monthly_analysis, entries_for_date
from report_generator import build_report_html, build_progress_tab_injection

# ── palette (matches report_generator.py) ─────────────────────────────────────
BUCKET_COLORS = {
    "Crosss-Functional/Governance": "#4A6FA5",
    "Inside/Pre-Sale": "#47A8BD",
    "Outside/Pre-Sale": "#5DB7A0",
    "Manufacturing": "#E8A838",
    "Post Shipment": "#C0604D",
}
_PALETTE = ["#4A6FA5", "#47A8BD", "#5DB7A0", "#E8A838", "#C0604D", "#8E7CC3", "#6B7A8D"]

_STYLE = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #F4F7FB; color: #2C3E50; }
.header { background: linear-gradient(135deg, #1E2A3A 0%, #3A4B5C 100%); color:#fff; padding: 32px 40px 24px; }
.header h1 { font-size: 26px; font-weight: 600; }
.header .sub { color:#b9c4d1; margin-top:6px; font-size:14px; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 28px 24px 60px; }
.kpis { display:grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap:16px; margin: 24px 0; }
.kpi { background:#fff; border:1px solid #DDE3ED; border-radius:10px; padding:18px 20px; }
.kpi .v { font-size:30px; font-weight:700; color:#4A6FA5; }
.kpi .l { font-size:12px; color:#6B7A8D; text-transform:uppercase; letter-spacing:.04em; margin-top:4px; }
.panel { background:#fff; border:1px solid #DDE3ED; border-radius:12px; padding:22px 24px; margin-bottom:22px; }
.panel h2 { font-size:17px; margin-bottom:14px; color:#1E2A3A; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
.chart-box { position:relative; height:280px; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
.card { border:1px solid #DDE3ED; border-radius:10px; padding:16px; background:#fff; }
.card .t { font-weight:600; font-size:15px; margin-bottom:8px; }
.card p { font-size:13px; color:#3A4B5C; margin:6px 0; }
.badge { display:inline-block; color:#fff; border-radius:6px; padding:3px 9px; font-size:11px; font-weight:600; margin:2px 4px 2px 0; }
.badge.up { background:#5DB7A0; } .badge.down { background:#C0604D; } .badge.flat { background:#6B7A8D; }
.badge.new { background:#E8A838; } .badge.recur { background:#4A6FA5; }
.src { font-size:12px; color:#6B7A8D; font-style:italic; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td { text-align:left; padding:9px 10px; border-bottom:1px solid #E7ECF3; }
th { background:#1F3864; color:#fff; font-size:12px; }
tr:nth-child(even) td { background:#F7F9FC; }
.empty { color:#6B7A8D; font-style:italic; padding:8px 0; }
.footer { text-align:center; color:#6B7A8D; font-size:12px; padding:20px; }
"""


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else ""


def _kpi(value, label) -> str:
    return f'<div class="kpi"><div class="v">{_esc(value)}</div><div class="l">{_esc(label)}</div></div>'


def _delta_badge(delta: int, kind: str) -> str:
    if delta > 0:
        return f'<span class="badge up">{kind} &uarr;{delta}</span>'
    if delta < 0:
        return f'<span class="badge down">{kind} &darr;{abs(delta)}</span>'
    return f'<span class="badge flat">{kind} &mdash;</span>'


def _colors_for(labels: list[str]) -> list[str]:
    return [BUCKET_COLORS.get(l, _PALETTE[i % len(_PALETTE)]) for i, l in enumerate(labels)]


def _page(title: str, header_title: str, subtitle: str, body: str, scripts: str) -> str:
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{_STYLE}</style>
</head><body>
<div class="header"><h1>{_esc(header_title)}</h1><div class="sub">{_esc(subtitle)}</div></div>
<div class="wrap">
{body}
</div>
<div class="footer">Electronics AI Working Group &middot; Trend Analysis &middot; Draft &mdash; all rows require human review before SharePoint promotion &middot; Generated {generated}</div>
<script>{scripts}</script>
</body></html>"""


# ── weekly report (canonical report layout + Trends tab) ──────────────────────

_TREND_TAB_STYLE = """
  .trend-badge { display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:11px; font-weight:600; color:#fff; margin:2px 4px 2px 0; white-space:nowrap; }
  .tb-up { background:#5DB7A0; } .tb-down { background:#C0604D; } .tb-flat { background:#6B7A8D; }
  .tb-new { background:#E8A838; } .tb-recur { background:#4A6FA5; }
  .trend-kpis { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:8px; }
  .trend-kpi { background:#fff; border:1px solid var(--border); border-radius:10px;
    padding:14px 20px; min-width:130px; }
  .trend-kpi .v { font-size:26px; font-weight:700; color:var(--blue); line-height:1; }
  .trend-kpi .l { font-size:11px; color:var(--muted); text-transform:uppercase;
    letter-spacing:.5px; margin-top:6px; }
  .trend-section-title { font-size:14px; font-weight:700; color:var(--dark);
    margin:28px 0 14px; }
  .trend-empty { color:var(--muted); font-style:italic; padding:8px 0; }
  .trend-card { background:#fff; border:1px solid var(--border); border-radius:12px;
    padding:16px 20px; box-shadow:0 2px 8px rgba(0,0,0,.05); }
  .trend-card .t { font-weight:700; font-size:15px; color:var(--dark); line-height:1.3; margin-bottom:8px; }
  .trend-card p { font-size:13px; color:var(--text); line-height:1.5; margin:6px 0; }
  .trend-card .src { font-size:12px; color:var(--muted); font-style:italic; margin-top:8px; }
"""


def _movement_badge(delta: int, kind: str) -> str:
    if delta > 0:
        return f'<span class="trend-badge tb-up">{kind} &uarr;{delta}</span>'
    if delta < 0:
        return f'<span class="trend-badge tb-down">{kind} &darr;{abs(delta)}</span>'
    return f'<span class="trend-badge tb-flat">{kind} &mdash;</span>'


def _trend_card(rec: dict, is_new: bool) -> str:
    if is_new:
        badges = '<span class="trend-badge tb-new">NEW THIS WEEK</span>'
    else:
        badges = f'<span class="trend-badge tb-recur">SEEN {rec["occurrences"]}x</span>'
        badges += _movement_badge(rec.get("signal_delta", 0), "Signal")
        badges += _movement_badge(rec.get("level_delta", 0), "Level")
    return f"""<div class="trend-card">
      <div class="t">{_esc(rec['title'])}</div>
      <div>{badges}</div>
      <p>{_esc(rec.get('evidence', ''))}</p>
      <p><strong>Bucket:</strong> {_esc(rec.get('bucket', '')) or '&mdash;'} &nbsp;
         <strong>Signal:</strong> {_esc(rec.get('signal', '')) or '&mdash;'}</p>
      <p><strong>Next step:</strong> {_esc(rec.get('next_step', '')) or '&mdash;'}</p>
      <div class="src">&mdash; {_esc(rec.get('speaker', '')) or 'Unknown'}</div>
    </div>"""


def _build_trends_tab(a: dict) -> tuple[str, str]:
    """Return (section_html, scripts) for the Trends tab injected into the report."""
    kpis = "".join(
        f'<div class="trend-kpi"><div class="v">{_esc(v)}</div><div class="l">{_esc(l)}</div></div>'
        for v, l in [
            (a["total"], "Opportunities This Week"),
            (a["new_count"], "New This Week"),
            (a["recurring_count"], "Carried Over"),
            (a["escalation_count"], "Escalating Signal"),
            (a["cumulative_total"], "Tracked All-Time"),
        ]
    )
    new_cards = "".join(_trend_card(r, True) for r in a["new_items"]) or \
        '<div class="trend-empty">No new opportunities this week.</div>'
    recur_cards = "".join(_trend_card(r, False) for r in a["recurring_items"]) or \
        '<div class="trend-empty">No carried-over opportunities this week.</div>'

    recent_labels = [r["date"] for r in a["recent_weeks"]]
    recent_vals = [r["count"] for r in a["recent_weeks"]]

    section = f"""<div id="tab-trends" class="section">
  <style>{_TREND_TAB_STYLE}</style>
  <div class="trend-kpis">{kpis}</div>
  <div class="trend-section-title">🆕 New This Week</div>
  <div class="cards-grid">{new_cards}</div>
  <div class="trend-section-title">🔁 Carried Over (week-over-week movement)</div>
  <div class="cards-grid">{recur_cards}</div>
  <div class="chart-card" style="margin-top:24px">
    <div class="chart-title">Opportunities per Week (recent)</div>
    <div class="chart-wrap"><canvas id="cTrend"></canvas></div>
  </div>
</div>"""

    scripts = f"""
new Chart(document.getElementById('cTrend'), {{
  type:'line',
  data:{{labels:{json.dumps(recent_labels)},datasets:[{{label:'Opportunities',data:{json.dumps(recent_vals)},borderColor:'#4A6FA5',backgroundColor:'rgba(74,111,165,.15)',fill:true,tension:.3,pointRadius:4}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{precision:0}}}}}}}}
}});"""
    return section, scripts


def generate_weekly_report(
    history: list[dict],
    meeting_date: date,
    out_path: str,
    week_rows: list[dict] | None = None,
    triage_rows: list[dict] | None = None,
) -> str:
    """
    Generate the weekly report using the canonical opportunity-report layout
    (Cards / Analytics / Full Table) over this week's opportunities, plus a
    4th "Trends" tab carrying the longitudinal insight (new vs. carried-over,
    week-over-week signal/level movement, and the per-week trend line).

    `week_rows` are this week's full classified rows; when omitted they are
    reconstructed from the history snapshots for the meeting date.
    `triage_rows` are low-confidence / excess rows excluded from primary surfaces.
    """
    a = weekly_analysis(history, meeting_date)
    if week_rows is None:
        week_rows = [snap for _, snap in entries_for_date(history, a["date"])]

    triage_rows = triage_rows or []
    n_suppressed = len(triage_rows)

    extra_nav = "<div class=\"nav-tab\" onclick=\"showTab('trends')\">📈 Trends</div>"
    section, scripts = _build_trends_tab(a)

    # Collect all historical rows across all weeks for Progress tab
    _weeks_dir = Path(__file__).parent.parent / "output" / "weeks"
    all_historical_rows: list[dict] = []
    for week_dir in sorted(_weeks_dir.glob("????-??-??")):
        p = week_dir / "classified_rows.json"
        if p.exists():
            week_date = week_dir.name
            try:
                rows_data = json.loads(p.read_text(encoding="utf-8"))
                for r in rows_data:
                    r_copy = dict(r)
                    r_copy.setdefault("_meeting_date", week_date)
                    all_historical_rows.append(r_copy)
            except Exception:
                pass
    progress_nav, progress_section = build_progress_tab_injection(all_historical_rows)
    extra_nav += "\n    " + progress_nav

    # Triage section (collapsible, omitted when empty)
    triage_section = ""
    if n_suppressed:
        triage_cards = "".join(
            f'<div class="triage-card"><div class="t">{_esc(r.get("Title",""))}</div>'
            f'<p>{_esc(r.get("EvidenceSummary",""))}</p>'
            f'<p class="src">Reason: {_esc(r.get("_triage_reason","low confidence"))}</p></div>'
            for r in triage_rows
        )
        triage_section = f"""
<details id="triage-section" style="margin-top:24px">
  <summary style="cursor:pointer;font-size:14px;font-weight:600;color:#7B3F00;padding:10px 0">
    ⚠ Triage / Low Confidence ({n_suppressed} candidates suppressed)
  </summary>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px">
    {triage_cards}
  </div>
</details>
<style>
.triage-card{{background:#FFF8F0;border:1px solid #E8C99A;border-radius:10px;padding:14px;}}
.triage-card .t{{font-weight:600;font-size:14px;margin-bottom:6px;color:#7B3F00;}}
.triage-card p{{font-size:12px;color:#5C4033;margin:4px 0;}}
.triage-card .src{{font-style:italic;color:#9E6B3F;}}
</style>"""

    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    suppressed_note = f", {n_suppressed} suppressed (low confidence)" if n_suppressed else ""

    # Review queue summary
    approved_count = sum(1 for r in week_rows if r.get("review_status") == "approved")
    rejected_count = sum(1 for r in week_rows if r.get("review_status") == "rejected")
    pending_count  = sum(1 for r in week_rows if not r.get("review_status"))
    review_summary = ""
    if week_rows:
        review_summary = (
            f" &middot; Review: "
            f"<span style='color:#155724'>✓ {approved_count} approved</span> / "
            f"<span style='color:#721c24'>✗ {rejected_count} rejected</span> / "
            f"<span style='color:#856404'>⏳ {pending_count} pending</span>"
        )

    header_sub = (f"Weekly Report &middot; {_esc(a['week'])} &middot; "
                  f"Meeting {_esc(a['date'])} &middot; "
                  f"{a['total']} opportunities identified{suppressed_note}"
                  f"{review_summary} &middot; "
                  f"Generated {generated}")

    html_out = build_report_html(
        week_rows,
        generated_date=generated,
        report_title=f"Electronics AI Working Group — Weekly Report {a['date']}",
        header_sub=header_sub,
        extra_nav=extra_nav,
        extra_sections=section + triage_section + progress_section,
        extra_scripts=scripts,
    )

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html_out, encoding="utf-8")
    suppressed_log = f", {n_suppressed} suppressed" if n_suppressed else ""
    print(f"[trend] weekly report ({a['total']} opps{suppressed_log}) -> {out_path}")
    return out_path


# ── monthly report ────────────────────────────────────────────────────────────

def _active_rows(active: list[dict]) -> str:
    trs = []
    for a in active:
        tag = '<span class="badge recur">Carry-over</span>' if a["is_carryover"] else '<span class="badge new">New</span>'
        trs.append(f"""<tr>
          <td>{_esc(a['title'])} {tag}</td>
          <td>{_esc(a['bucket'])}</td>
          <td>{_esc(a['type'])}</td>
          <td>{_esc(a['signal'])}</td>
          <td>{_esc(a['level'])}</td>
          <td style="text-align:center">{a['month_occurrences']}</td>
          <td style="text-align:center">{a['total_occurrences']}</td>
          <td>{_esc(a['first_seen'])}</td>
          <td>{_esc(a['last_seen'])}</td>
        </tr>""")
    return "".join(trs) or '<tr><td colspan="9" class="empty">No opportunities this month.</td></tr>'


def _escalation_rows(escalations: list[dict]) -> str:
    if not escalations:
        return '<tr><td colspan="3" class="empty">No escalations detected this month.</td></tr>'
    trs = []
    for e in escalations:
        moves = []
        if e["signal_delta"] > 0:
            moves.append(f'{_esc(e["signal_from"]) or "&mdash;"} &rarr; {_esc(e["signal_to"])}')
        if e["level_delta"] > 0:
            moves.append(f'{_esc(e["level_from"]) or "&mdash;"} &rarr; {_esc(e["level_to"])}')
        trs.append(f'<tr><td>{_esc(e["title"])}</td>'
                   f'<td>{_delta_badge(e["signal_delta"], "Signal")}{_delta_badge(e["level_delta"], "Level")}</td>'
                   f'<td>{"<br>".join(moves)}</td></tr>')
    return "".join(trs)


def generate_monthly_report(history: list[dict], month: str, out_path: str) -> str:
    a = monthly_analysis(history, month)

    kpis = "".join([
        _kpi(a["unique_total"], "Unique Opportunities"),
        _kpi(a["weeks_covered"], "Weeks Covered"),
        _kpi(a["new_total"], "New This Month"),
        _kpi(a["carryover_total"], "Carried From Prior"),
        _kpi(a["escalation_count"], "Escalating"),
    ])

    week_labels = [w["date"] for w in a["per_week"]]
    totals = [w["total"] for w in a["per_week"]]
    new_vals = [w["new"] for w in a["per_week"]]
    recur_vals = [w["recurring"] for w in a["per_week"]]

    # Stacked bucket-by-week dataset.
    all_buckets = sorted({b for d in a["bucket_by_week"].values() for b in d if b is not None})
    bucket_datasets = []
    for i, b in enumerate(all_buckets):
        bucket_datasets.append({
            "label": b,
            "data": [a["bucket_by_week"].get(d, {}).get(b, 0) for d in week_labels],
            "backgroundColor": BUCKET_COLORS.get(b, _PALETTE[i % len(_PALETTE)]),
        })

    type_labels = list(a["type_distribution"].keys())
    type_vals = list(a["type_distribution"].values())

    body = f"""
    <div class="kpis">{kpis}</div>
    <div class="panel"><h2>Opportunities per Week</h2><div class="chart-box"><canvas id="mPerWeek"></canvas></div></div>
    <div class="grid2">
      <div class="panel"><h2>Operating Bucket by Week</h2><div class="chart-box"><canvas id="mBucket"></canvas></div></div>
      <div class="panel"><h2>AI Use Case Type (month)</h2><div class="chart-box"><canvas id="mType"></canvas></div></div>
    </div>
    <div class="panel"><h2>Signal / Level Momentum</h2>
      <table><thead><tr><th>Opportunity</th><th>Movement</th><th>Detail</th></tr></thead>
      <tbody>{_escalation_rows(a['escalations'])}</tbody></table>
    </div>
    <div class="panel"><h2>All Opportunities Active This Month</h2>
      <table><thead><tr><th>Title</th><th>Bucket</th><th>Type</th><th>Signal</th><th>Level</th>
      <th>Mo.&nbsp;hits</th><th>Total&nbsp;hits</th><th>First seen</th><th>Last seen</th></tr></thead>
      <tbody>{_active_rows(a['active'])}</tbody></table>
    </div>
    """

    scripts = f"""
    new Chart(document.getElementById('mPerWeek'), {{
      type:'line',
      data:{{labels:{json.dumps(week_labels)},datasets:[
        {{label:'Total',data:{json.dumps(totals)},borderColor:'#4A6FA5',backgroundColor:'rgba(74,111,165,.12)',fill:true,tension:.3}},
        {{label:'New',data:{json.dumps(new_vals)},borderColor:'#E8A838',tension:.3}},
        {{label:'Recurring',data:{json.dumps(recur_vals)},borderColor:'#5DB7A0',tension:.3}}
      ]}},
      options:{{responsive:true,maintainAspectRatio:false,scales:{{y:{{beginAtZero:true,ticks:{{precision:0}}}}}}}}
    }});
    new Chart(document.getElementById('mBucket'), {{
      type:'bar',
      data:{{labels:{json.dumps(week_labels)},datasets:{json.dumps(bucket_datasets)}}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},
        scales:{{x:{{stacked:true}},y:{{stacked:true,beginAtZero:true,ticks:{{precision:0}}}}}}}}
    }});
    new Chart(document.getElementById('mType'), {{
      type:'doughnut',
      data:{{labels:{json.dumps(type_labels)},datasets:[{{data:{json.dumps(type_vals)},backgroundColor:{json.dumps(_colors_for(type_labels))},borderWidth:2,borderColor:'#fff'}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}}}}
    }});
    """

    try:
        pretty_month = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
    except ValueError:
        pretty_month = month
    subtitle = f"{pretty_month} &middot; {a['weeks_covered']} week(s) analyzed"
    page = _page("Monthly AI Opportunity Trend", "Monthly AI Opportunity Trend", subtitle, body, scripts)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(page, encoding="utf-8")
    print(f"[trend] monthly report ({a['unique_total']} unique opps) -> {out_path}")
    return out_path
