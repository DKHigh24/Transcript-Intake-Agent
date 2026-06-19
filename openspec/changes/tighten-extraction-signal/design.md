## Context

The extractor currently runs in maximum-recall mode: every AI-adjacent mention in every chunk is emitted as a candidate. A 1-hour session with 9 keyword-filtered chunks routinely produces 40–44 candidates. At classification time, the LLM treats each candidate independently, so near-duplicate ideas originating from different chunks of the same conversation are preserved as distinct rows. The result is an inflated workbook that makes human review harder and erodes stakeholder trust.

Three independent problems compound each other:
1. **Prompt specificity** — the extraction prompt does not require a minimum level of speaker commitment or actionability.
2. **Cross-chunk duplication** — the same idea, raised in different chunks, becomes 2–4 separate candidates with slightly different wording.
3. **No downstream filter** — low-confidence rows flow into the same review table as high-confidence rows, with no way to separate signal from noise.

## Goals / Non-Goals

**Goals:**
- Reduce average candidates per session from ~35 to a target of 10–18 without losing genuinely distinct, actionable opportunities
- Merge near-duplicate candidates within a session before classification (saves LLM cost and reduces noise)
- Suppress low-confidence rows from primary review surfaces while preserving them for traceability
- Make thresholds configurable via `.env` so they can be tuned without code changes

**Non-Goals:**
- Cross-session deduplication (already handled by `opportunity_matcher.py`)
- Changing the classification schema or SharePoint field mapping
- Retroactively re-extracting historical weeks (back-fill via `backfill_maturity_signal.py` pattern is out of scope)
- Eliminating the LLM extractor and replacing with purely rule-based extraction

## Decisions

### Decision 1 — Tighten the extraction prompt with an explicit substantiveness rubric

**Chosen**: Add a numbered exclusion list to `skills/extract_opportunities.md` that the LLM must apply before emitting a candidate. A candidate requires: (a) a named or implied actor, (b) a specific tool/domain, and (c) one of: active delivery, active piloting, or a concrete proposal with a next step implied.

**Alternatives considered**:
- *Post-extraction scoring*: Run a second LLM call to score each candidate — rejected because it doubles token cost with marginal benefit over a better prompt.
- *Regex keyword gate*: Keep only candidates whose evidence contains high-signal phrases — rejected because it would miss paraphrased delivery confirmations.

### Decision 2 — Deterministic fuzzy deduplication in Python, not LLM

**Chosen**: After extraction, compare all candidate titles + evidence within the session using `difflib.SequenceMatcher` ratio. Pairs above a `DEDUP_SIMILARITY_THRESHOLD` (default 0.72) are merged: keep the candidate with the longer EvidenceSummary, discard the other. This is deterministic, cheap, and auditable.

**Alternatives considered**:
- *LLM-based dedup*: Ask the model to merge candidates — rejected because it adds latency, cost, and non-determinism at a step where determinism is preferred.
- *Exact title match only*: Too brittle; the same idea rephrased across chunks would not be caught.

### Decision 3 — Confidence floor as a filter, not a gate

**Chosen**: Low-confidence rows are not discarded — they are moved to a second Excel sheet ("Triage") in `review_rows.xlsx` and excluded from `master_opportunities.xlsx` and HTML report cards by default. A `--include-low-confidence` CLI flag re-admits them to all surfaces.

**Rationale**: Discarding is irreversible and loses traceability. A second sheet preserves auditability while keeping the primary review surface clean.

### Decision 4 — `MAX_CANDIDATES_PER_SESSION` as a soft guardrail

**Chosen**: If post-dedup candidate count exceeds the limit (default 20), the pipeline emits a `[warning]` log line and routes excess candidates (lowest confidence first) to the Triage sheet rather than blocking the run. No hard failure.

**Rationale**: A hard limit would create confusing silent drops. A soft guardrail surfaces the issue to the operator without interrupting the weekly workflow.

## Risks / Trade-offs

- **[Risk] Tighter prompt may miss valid low-signal opportunities** → Mitigation: The Triage sheet captures everything excluded; operators can promote rows manually. The threshold is configurable.
- **[Risk] Fuzzy dedup threshold tuning** → Mitigation: Default 0.72 is conservative (misses only near-identical phrasing). Configurable via `DEDUP_SIMILARITY_THRESHOLD` in `.env`.
- **[Risk] Historical data not updated** → Mitigation: Explicitly out of scope; existing archived rows are unaffected. Future re-runs of historical transcripts will produce cleaner output.
- **[Trade-off] Reduced row count may look like "less activity"** → The weekly HTML report will display a "candidates suppressed" count so the reduction is transparent to reviewers.

## Migration Plan

1. Deploy extraction prompt change — all future runs immediately benefit.
2. Deploy deduplication step — runs automatically; no schema change.
3. Deploy confidence filter + Triage sheet — `review_rows.xlsx` gains a second sheet; downstream Power BI only reads the main sheet (no impact).
4. No rollback required; thresholds can be relaxed via `.env` without redeployment.

## Open Questions

- Should the Triage sheet be included in the HTML report as a collapsed section, or omitted entirely? (Proposal includes it; can be removed if stakeholders prefer cleaner output.)
- What is the right default for `MAX_CANDIDATES_PER_SESSION`? Starting at 20; validate after first 2 runs.
