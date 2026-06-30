# Overview

Plain-language documentation of how the **AI Transcript Intake Agent** works and
how to keep it running week to week.

## Contents

- **[`process_overview.html`](process_overview.html)** — a self-contained, visual
  walkthrough of the whole system:
  - 🔄 an end-to-end **flowchart** (upload → read → clean → chunk → extract 🧠 →
    classify 🧠 → validate → workbook / payload / HTML → archive + history →
    weekly report → monthly rollup → human review → opt-in SharePoint push →
    **opt-in ADO push → live ADO sync → Progress tab**),
  - 🧩 a stage-by-stage table (module + inputs/outputs + which steps use AI),
  - 📅 weekly operation, 🤖 the automatic folder watcher, 🗓 the monthly rollup,
  - 🔗 ADO integration — how `--push-ado` closes the loop and how the weekly sync works,
  - 📂 the output layout, 🛠 a maintenance checklist + core rules, and
  - 🚑 a troubleshooting table.
- **[`code_execution_line_diagram.html`](code_execution_line_diagram.html)** — a
  detailed line-by-line execution map showing actual script/module call paths:
  - `main.py` mode routing (`weekly`, `review`, `eval`, etc.),
  - the watcher subprocess path (`watch_transcripts.py -> main.py --mode weekly`),
  - ADO standalone utility path (`ado_client.py --sync/--push-all`), and
  - explicit AI-boundary callouts (`candidate_detector`, `classifier`, presentation content).

It is a single HTML file (Chart.js-style palette, no build step) — just open it
in any browser.

## Open it

From the repository root:

```powershell
# Windows / PowerShell — convenience script
./Overview/open_overview.ps1

# …or open directly
Invoke-Item "Overview/process_overview.html"
Invoke-Item "Overview/code_execution_line_diagram.html"
```

```bash
# macOS
open Overview/process_overview.html
# Linux
xdg-open Overview/process_overview.html
```

## Keeping the document accurate

This is documentation, not code — update it whenever the pipeline changes
(new stage, new mode, renamed module, changed output paths). The flowchart is a
hand-built inline SVG inside `process_overview.html`; edit the `<rect>` / `<text>`
/ `<path>` blocks in the `#flow` section to reflect new steps.

Key things to keep in sync with `README.md`:
- Pipeline step list (currently Steps 0–12)
- ADO integration description (Step 0 sync, Step 9c push, Progress tab)
- Output layout (especially ADO columns AS–AY in `master_opportunities.xlsx`, with `WeekDate` at AR)
- Command-line examples (especially `--push-ado` and `--sync`)
- The weekly checklist in the "Keeping It Running" section
