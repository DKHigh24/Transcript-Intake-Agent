# Skill: Weekly Report HTML Format

The weekly HTML output **must** use the same layout and behavior as the original
`output/ai_opportunity_report.html`. That layout is the canonical "opportunity
report" format for this project. Do not invent a new layout for the weekly report.

## Single source of truth

`src/report_generator.py` owns the canonical layout via:

```python
build_report_html(
    rows,                       # list of classified opportunity rows
    generated_date=None,        # defaults to now
    report_title=...,           # <title> text
    header_sub=None,            # header sub-line (defaults to "AI Opportunity Intake Report · Generated ...")
    extra_nav="",               # extra nav-tab buttons (HTML)
    extra_sections="",          # extra .section blocks (HTML)
    extra_scripts="",           # extra JS appended after built-in chart setup
) -> str
```

- `generate_report()` (single transcript) calls `build_report_html(rows)` with no extras.
- `generate_weekly_report()` in `src/trend_reporter.py` calls `build_report_html(...)`
  with `week_rows` and injects a **4th "Trends" tab** via the `extra_*` parameters.

Any report that shows opportunities must go through `build_report_html`. Never
hand-roll a separate HTML skeleton, palette, or tab system for opportunity output.

## Required layout (do not change)

A single self-contained HTML file (Chart.js loaded from the jsDelivr CDN, no build
step, no local assets) containing, in order:

1. **Header** — `⚡ Electronics AI Working Group` title, a configurable sub-line, a
   right-aligned meta block (`Source / Status: All Needs Review / Human Review Required`),
   and a KPI row: Opportunities, High Signal, Action/Both, Avg Value Score, High Confidence.
2. **Nav tabs** — `📋 Opportunity Cards`, `📊 Analytics`, `🗂 Full Table`, then any extra tabs.
3. **Opportunity Cards tab** — filter buttons (All + per-bucket + per-type) and a
   `.cards-grid` of `.card` elements (`data-bucket` / `data-type` / `data-signal` for filtering).
4. **Analytics tab** — donut charts (`chartBucket`, `chartType`), bar charts
   (`chartSignal`, `chartLevel`), and the Average Scores panel.
5. **Full Table tab** — the 13-column table (Title, Bucket, Type, Process Stage,
   Level, Signal, Tool, Owner/SME, Val, Eff, Risk, Ready, Conf).
6. **Footer** — draft disclaimer: all rows require human review before SharePoint promotion.
7. **Scripts** — `showTab()`, `filterCards()`, `makeDonut()`, `makeBar()`, the four
   built-in chart instantiations, then any `extra_scripts`.

The interactive behavior (tab switching, card filtering, charts) must keep working
exactly as in the original.

## Color palette (fixed)

Use the palette already defined in `report_generator.py`: `BUCKET_COLORS`,
`TYPE_COLORS`, `SIGNAL_COLORS`, `LEVEL_COLORS`, and the CSS `:root` variables
(`--blue #4A6FA5`, `--teal #47A8BD`, `--green #5DB7A0`, `--amber #E8A838`,
`--red #C0604D`, `--dark #1E2A3A`, etc.). Do not introduce new brand colors.

## The weekly "Trends" tab

The weekly report adds longitudinal insight as a **4th tab only** — it never alters
the first three tabs. It is built in `trend_reporter._build_trends_tab(a)` from
`weekly_analysis(history, meeting_date)` and contains:

- 5 trend KPIs: Opportunities This Week, New This Week, Carried Over, Escalating Signal, Tracked All-Time.
- "New This Week" cards and "Carried Over" cards (with week-over-week Signal/Level
  movement badges: `tb-up` / `tb-down` / `tb-flat`, plus `tb-new` / `tb-recur`).
- A "Opportunities per Week" line chart (`cTrend`).

Trend-only CSS is scoped under `_TREND_TAB_STYLE` and injected inside the trends
section so the shared template stays untouched. Trend classes are prefixed
(`trend-*`, `tb-*`) and reuse the shared template classes (`.cards-grid`,
`.chart-card`, `.chart-wrap`, `:root` vars) wherever possible.

## How to add another tab (pattern to follow)

1. Build the section HTML with `id="tab-<name>"` and class `section`.
2. Add a nav button: `<div class="nav-tab" onclick="showTab('<name>')">…</div>` via `extra_nav`.
3. Put any chart/JS in `extra_scripts` (it runs after the built-in charts; Chart.js is loaded).
4. Pass all three through `build_report_html(..., extra_nav=, extra_sections=, extra_scripts=)`.
5. Keep new CSS scoped (prefixed classes in an inline `<style>` inside the section)
   so the canonical template is never edited for one-off tabs.

## Constraints

- Self-contained single `.html` file; only external dependency is the Chart.js CDN script.
- No new Python dependencies.
- All output remains **draft / Needs Review**; keep the human-review footer.
- Do not send transcripts to the model to build reports — reports render from
  `classified_rows.json` / history snapshots only.
- `header_sub` and other injected values must not contain `{`/`}` that would break
  `str.format` substitution in the template.

## Verification checklist

After changing report code, regenerate a report and confirm:

- 4 nav tabs present; `tab-trends` and `showTab('trends')` exist for weekly.
- Card count and table-row count equal the number of opportunities.
- `chartBucket` (Analytics) and `cTrend` (Trends) canvases exist.
- No leftover unescaped `{placeholder}` text remains in the HTML.
- The single-transcript report still renders with **no** trends tab.

Offline regeneration (no OpenAI key needed):

```bash
python -c "import sys; sys.path.insert(0,'src'); from datetime import date; \
from history_store import load_history; from trend_reporter import generate_weekly_report; \
generate_weekly_report(load_history(), date(2026,6,10), 'output/_check.html')"
```
