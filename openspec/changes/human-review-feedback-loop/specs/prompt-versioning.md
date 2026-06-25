# Spec: Prompt Versioning and Feedback Staging

## Purpose

Allow accumulated reviewer feedback to improve future classification quality through
a controlled, versioned, human-approved process. No automatic self-modification.

## Requirements

### Requirement: Feedback is staged before promotion

**WHEN** `--mode apply-feedback` is run
**THEN** a staging directory SHALL be created at `config/feedback_staging/<version>/`
containing:
- `proposed_examples.jsonl` — few-shot examples derived from reviewer corrections
- `proposed_rules.md` — plain-English rule delta suggestions based on correction patterns
- `version.yaml` — version tag, date, summary of changes, example count

**AND** the canonical classifier (`src/classifier.py`, `skills/classify_opportunities.md`)
SHALL NOT be modified at this stage.

### Requirement: Promotion requires passing evaluation

**WHEN** `--mode promote-feedback --feedback-version <v>` is run
**THEN** the system SHALL check that `output/eval/` contains a passing eval report
for the current examples version
**AND** if no passing eval report exists, promotion SHALL be blocked with:
```
[feedback] Promotion blocked: no passing eval report found.
Run --mode eval first. Current threshold: 80%.
```

### Requirement: Promotion is explicit and traceable

**WHEN** `--promote-feedback` passes the eval gate
**THEN** proposed examples SHALL be appended to `config/eval/examples.jsonl`
**AND** proposed rule delta SHALL be appended to `skills/classify_opportunities.md`
**AND** `config/feedback_staging/<version>/promoted.yaml` SHALL be written with:
  - `promoted_at`: ISO timestamp
  - `examples_added`: count
  - `by`: reviewer_id

### Requirement: Staging is committed and reviewable

**WHEN** staging files are written
**THEN** they SHALL be committed to git as part of the feature branch
so that the team can review proposed changes via pull request before promotion.

### Requirement: Version tags prevent collisions

**WHEN** auto-generating a version tag
**THEN** the tag SHALL follow the format `v<YYYYMMDD>` or `v<YYYYMMDD>-<N>` if
a same-day version already exists.

## Non-functional

- Staging files are committed (not gitignored) — they are proposals, not generated output
- No model API call is made during `--apply-feedback` — it is deterministic pattern analysis
- The promotion step does make model calls (via `--eval`) but those are read-only and
  produce a report, not a modification
- All modifications to `src/classifier.py` or `skills/*.md` require a git commit,
  ensuring a full audit trail in git log
