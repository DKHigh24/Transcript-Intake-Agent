# Overview

Plain-language documentation of how the **AI Transcript Intake Agent** works and
how to keep it running week to week.

## Contents

- **[`process_overview.html`](process_overview.html)** — a self-contained, visual
  walkthrough of the whole system:
  - 🔄 an end-to-end **flowchart** (upload → read → clean → chunk → extract 🧠 →
    classify 🧠 → validate → workbook / payload / HTML → archive + history →
    weekly report → monthly rollup → human review → opt-in SharePoint push),
  - 🧩 a stage-by-stage table (module + inputs/outputs + which steps use AI),
  - 📅 weekly operation, 🤖 the automatic folder watcher, 🗓 the monthly rollup,
  - 📂 the output layout, 🛠 a maintenance checklist + core rules, and
  - 🚑 a troubleshooting table.

It is a single HTML file (Chart.js-style palette, no build step) — just open it
in any browser.

## Open it

From the repository root:

```powershell
# Windows / PowerShell — convenience script
./Overview/open_overview.ps1

# …or open directly
Invoke-Item "Overview/process_overview.html"
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
/ `<path>` blocks in the `#flow` section to reflect new steps. Keep it consistent
with the project `README.md` and `skills/weekly_report_format.md`.
