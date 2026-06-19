## Context

The pipeline currently extracts AI opportunity candidates and classifies them into a SharePoint
MVP schema. All extracted opportunities — whether someone said "we should build this someday" or
"this is already running in production" — receive identical treatment. The `CurrentStatus` field
captures workflow state (Needs Review, In Evaluation, etc.) but does not capture the *maturity
signal* embedded in the original speaker evidence.

The group's transcripts contain clear linguistic patterns that distinguish three distinct states:
aspirational ideas, work in progress/piloting, and delivered/working tools. Surfacing this as a
first-class field enables leadership to track real delivery velocity alongside the pipeline of ideas.

## Goals / Non-Goals

**Goals:**
- Add a `MaturitySignal` field inferred by the LLM during classification from verbatim evidence
- Surface the field as a visual badge on HTML report cards (color-coded)
- Include `MaturitySignal` in `master_opportunities.xlsx` and `review_rows.xlsx` for Power BI
- Add a "Live Wins" section to the PPTX deck when `Delivered / Active Today` rows are present
- Default to `"Unknown"` when the evidence is ambiguous — never force a signal

**Non-Goals:**
- Modifying `CurrentStatus` — that field remains the human workflow tracker
- Auto-promoting SharePoint status based on `MaturitySignal`
- Back-filling historical transcripts automatically (they will get `""` / `"Unknown"` until re-run)
- Building a separate NLP classifier — the existing LLM classification step handles this

## Decisions

**Decision 1: Infer at classification, not extraction**
Maturity signal is inferred from the full evidence summary during the classification step
(classifier.py / skills/classify_opportunities.md) rather than at extraction time.
*Rationale*: The classifier already has the full candidate context; the extractor is chunked
and stateless. Adding this to the classifier requires one prompt update vs. two.
*Alternative considered*: Flag signal phrases during extraction (candidate_detector.py) — rejected
because the extractor sees raw chunks without full candidate context and the signal sometimes
spans what the extractor sees as a sentence boundary.

**Decision 2: Four-value controlled vocabulary**
`MaturitySignal` choices: `Aspirational`, `In Progress / Piloting`, `Delivered / Active Today`, `Unknown`.
*Rationale*: Matches the three natural states in transcripts plus an explicit unknown. Four
values are actionable in Power BI slicers. Finer granularity (e.g. "Retired") is out of scope.

**Decision 3: Linguistic marker examples in classifier prompt**
The classifier skill will include example phrases for each value rather than relying on the
model's general judgment. This reduces hallucination of maturity signals.
*Examples*:
- Aspirational: "we should...", "what if...", "I'd love to see...", "has anyone tried..."
- In Progress: "we're currently...", "we started...", "proof of concept", "in evaluation"
- Delivered: "we're already using...", "this is live...", "we deployed...", "it's running"

**Decision 4: Column position in XLSX**
`MaturitySignal` is inserted immediately after `ConfidenceLevel` (column F) in both
`review_rows.xlsx` and `master_opportunities.xlsx`, making it column G. This keeps the
signal-quality fields grouped: Confidence → Maturity → AIUseCaseType.

## Risks / Trade-offs

- **LLM ambiguity** → Some speakers hedge ("we sort of have this running..."). Default to
  `"Unknown"` and let human review correct it. The badge will be gray for Unknown.
- **Prompt inflation** → Adding examples to the classifier prompt increases token usage slightly.
  Mitigated by keeping examples concise (one phrase each, not paragraphs).
- **Historical rows** → Archived classified_rows.json files pre-dating this change won't have
  `MaturitySignal`. They will render as `"—"` on cards and blank in XLSX. Re-running all
  transcripts with `--mode weekly` per transcript back-fills the field.

## Migration Plan

1. Update config files (additive — no existing field changes)
2. Update skills (prompt updates — next run picks them up automatically)
3. Update src/ files (card rendering, XLSX columns)
4. Re-run all transcripts to back-fill `MaturitySignal` in archived rows and master XLSX
5. No rollback needed — field is optional; removing it from config is sufficient to revert
