# Spec: Evaluation and Regression Testing

## Purpose

Provide a repeatable, quantitative way to measure classifier quality and to prevent
feedback-driven prompt changes from degrading performance on known-good examples.

## Requirements

### Requirement: Eval dataset is persistent and committed

`config/eval/examples.jsonl` SHALL be committed to the repository.

Each example SHALL contain:
```json
{
  "evidence": "<transcript chunk used as classifier input>",
  "expected": {
    "<field>": "<expected value>",
    ...
  },
  "source": "reviewer",
  "date_added": "<YYYY-MM-DD>"
}
```

The minimum dataset size for an eval run is 5 examples. Below 5, `--mode eval`
SHALL print a warning and exit.

### Requirement: Eval runs classifier against labelled examples

**WHEN** `--mode eval` is run
**THEN** for each example in `config/eval/examples.jsonl`:
1. Pass `evidence` as input to the current classifier (real AI call)
2. Compare output against `expected` fields
3. Record match/mismatch per field

**AND** produce a summary report at `output/eval/eval_<timestamp>.json` with:
- `total_examples`: int
- `overall_accuracy`: float (0.0 - 1.0)
- `per_field_accuracy`: dict of field -> float
- `pass`: bool (True if `overall_accuracy >= threshold`)
- `threshold`: float
- `timestamp`: ISO string

### Requirement: Threshold is configurable

Default threshold: 0.80 (80% overall accuracy).

Override via `FEEDBACK_PROMOTION_THRESHOLD` in `.env` (float, 0.0–1.0).

### Requirement: Regression detection

**WHEN** two or more eval reports exist
**THEN** `--mode eval` SHALL compare the current run against the previous run
**AND** highlight fields where accuracy decreased by more than 5 percentage points

### Requirement: Eval result is required for promotion

**WHEN** `--mode promote-feedback` is run
**THEN** the most recent eval report for the candidate version SHALL exist
**AND** `pass` SHALL be `True` in that report
**OTHERWISE** promotion SHALL be blocked (see prompt-versioning spec)

## Non-functional

- The eval command makes real AI calls — it is the only part of the feedback loop
  that incurs LLM cost
- Eval reports are written to `output/eval/` (gitignored — generated artifacts)
- The examples file `config/eval/examples.jsonl` is committed — it is source data
- Running eval multiple times is safe (writes new timestamped files, does not overwrite)
