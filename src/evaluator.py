"""
evaluator.py
Runs the current classifier against a labelled eval dataset and reports accuracy.

Eval examples live in config/eval/examples.jsonl.
Each example:
  {
    "evidence": "<transcript chunk>",
    "expected": {"field": "value", ...},
    "source": "reviewer",
    "date_added": "YYYY-MM-DD"
  }

Public API:
    load_examples()                   -> list[dict]
    run_eval(examples)                -> dict (results)
    write_eval_report(results)        -> Path
    passes_threshold(results, thresh) -> bool
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent / "config"
EVAL_EXAMPLES_PATH = _CONFIG_DIR / "eval" / "examples.jsonl"
_EVAL_OUTPUT_DIR = Path("output") / "eval"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ── Load examples ─────────────────────────────────────────────────────────────

def load_examples() -> list[dict]:
    """Load all labelled examples from the eval dataset."""
    if not EVAL_EXAMPLES_PATH.exists():
        return []
    examples = []
    for line in EVAL_EXAMPLES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return examples


# ── Run eval ─────────────────────────────────────────────────────────────────

def run_eval(examples: list[dict]) -> dict:
    """
    Run the current classifier against each example and compute accuracy.

    Makes real LLM calls — this is the only step in the feedback pipeline
    that incurs model cost.
    """
    from classifier import classify_candidates

    threshold = float(os.getenv("FEEDBACK_PROMOTION_THRESHOLD", "0.80"))

    field_correct: dict[str, int] = {}
    field_total: dict[str, int] = {}
    detail: list[dict] = []

    for i, ex in enumerate(examples):
        evidence = ex.get("evidence", "")
        expected = ex.get("expected", {})
        if not evidence or not expected:
            continue

        # Build a minimal candidate so classify_candidates can process it
        candidate = {
            "candidate_title": f"Eval example {i+1}",
            "evidence_summary": evidence,
            "source_speaker": "",
            "source_timestamp": "",
            "confidence": "Medium",
        }

        try:
            rows = classify_candidates([candidate], output_path=os.devnull)
            if not rows:
                continue
            actual = rows[0]
        except Exception as e:
            print(f"  [eval] Example {i+1} classification failed: {e}")
            continue

        row_detail = {"example": i + 1, "field_results": {}}
        for field, expected_val in expected.items():
            actual_val = actual.get(field)
            match = str(actual_val).strip().lower() == str(expected_val).strip().lower()
            field_correct[field] = field_correct.get(field, 0) + (1 if match else 0)
            field_total[field] = field_total.get(field, 0) + 1
            row_detail["field_results"][field] = {
                "expected": expected_val,
                "actual": actual_val,
                "match": match,
            }

        detail.append(row_detail)
        print(f"  [eval] {i+1}/{len(examples)}: {sum(v['match'] for v in row_detail['field_results'].values())}"
              f"/{len(expected)} fields correct")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    per_field_accuracy = {
        field: field_correct.get(field, 0) / field_total[field]
        for field in field_total
    }

    if per_field_accuracy:
        overall = sum(per_field_accuracy.values()) / len(per_field_accuracy)
    else:
        overall = 0.0

    return {
        "total_examples": len(examples),
        "evaluated": len(detail),
        "overall_accuracy": overall,
        "per_field_accuracy": per_field_accuracy,
        "pass": overall >= threshold,
        "threshold": threshold,
        "timestamp": _now_iso(),
        "detail": detail,
    }


# ── Write report ──────────────────────────────────────────────────────────────

def write_eval_report(results: dict) -> Path:
    """Write evaluation results to output/eval/eval_<timestamp>.json."""
    _EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _EVAL_OUTPUT_DIR / f"eval_{_now_ts()}.json"
    report_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report_path


# ── Threshold check ───────────────────────────────────────────────────────────

def passes_threshold(results: dict, threshold: float | None = None) -> bool:
    """Return True if the eval results meet the accuracy threshold."""
    if threshold is None:
        threshold = float(os.getenv("FEEDBACK_PROMOTION_THRESHOLD", "0.80"))
    return results.get("overall_accuracy", 0.0) >= threshold
