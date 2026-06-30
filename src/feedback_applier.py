"""
feedback_applier.py
Converts accumulated reviewer feedback into staged prompt/example proposals.

All output goes to config/feedback_staging/<version>/.
Nothing in the canonical classifier or skill files is changed here —
those changes happen only via --mode promote-feedback after eval passes.

Public API:
    build_staged_version(version, records) -> Path  (staging dir)
    promote_version(version)                -> None  (applies to canonical files)
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_STAGING_BASE = _CONFIG_DIR / "feedback_staging"
_EVAL_EXAMPLES_PATH = _CONFIG_DIR / "eval" / "examples.jsonl"
_SKILLS_DIR = Path(__file__).parent.parent / "skills"
_CLASSIFY_SKILL = _SKILLS_DIR / "classify_opportunities.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _auto_version() -> str:
    """Generate a version tag like v20260625 or v20260625-2 if same day exists."""
    base = "v" + datetime.now(timezone.utc).strftime("%Y%m%d")
    if not (_STAGING_BASE / base).exists():
        return base
    for i in range(2, 20):
        candidate = f"{base}-{i}"
        if not (_STAGING_BASE / candidate).exists():
            return candidate
    return base + "-x"


def _get_reviewer_id() -> str:
    rid = os.getenv("REVIEWER_ID", "").strip()
    if rid:
        return rid
    try:
        return os.getlogin()
    except Exception:
        return "unknown"


# ── Build staging ─────────────────────────────────────────────────────────────

def build_staged_version(version: str | None, records: list[dict]) -> Path:
    """
    Convert feedback records into a staged version directory.

    Returns the path to the created staging directory.
    """
    if not version:
        version = _auto_version()

    staging_dir = _STAGING_BASE / version
    staging_dir.mkdir(parents=True, exist_ok=True)

    edits = [r for r in records if r.get("event") == "field_edit"]
    approvals = [r for r in records if r.get("event") == "approve"]
    rejections = [r for r in records if r.get("event") == "reject"]

    # ── proposed_examples.jsonl ───────────────────────────────────────────────
    examples = _extract_examples(edits)
    examples_path = staging_dir / "proposed_examples.jsonl"
    with open(examples_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # ── proposed_rules.md ────────────────────────────────────────────────────
    rule_delta = _draft_rule_delta(edits)
    (staging_dir / "proposed_rules.md").write_text(rule_delta, encoding="utf-8")

    # ── version.yaml ─────────────────────────────────────────────────────────
    version_meta = (
        f"version: {version}\n"
        f"created_at: {_now_iso()}\n"
        f"created_by: {_get_reviewer_id()}\n"
        f"total_feedback_records: {len(records)}\n"
        f"field_edits: {len(edits)}\n"
        f"approvals: {len(approvals)}\n"
        f"rejections: {len(rejections)}\n"
        f"proposed_examples: {len(examples)}\n"
        f"status: staged\n"
    )
    (staging_dir / "version.yaml").write_text(version_meta, encoding="utf-8")

    return staging_dir


def _extract_examples(edits: list[dict]) -> list[dict]:
    """
    Build proposed few-shot examples from field edit records.

    Each example pairs the reviewer-corrected value against the model value
    so the LLM can learn from the correction.
    """
    examples = []
    for edit in edits:
        field = edit.get("field", "")
        model_val = edit.get("model_value", "")
        reviewer_val = edit.get("reviewer_value", "")
        if not field or model_val == reviewer_val:
            continue
        examples.append({
            "type": "field_correction",
            "field": field,
            "model_value": model_val,
            "reviewer_value": reviewer_val,
            "opportunity_id": edit.get("opportunity_id", ""),
            "date": edit.get("date", ""),
            "notes": edit.get("reviewer_notes"),
        })
    return examples


def _draft_rule_delta(edits: list[dict]) -> str:
    """
    Analyse edit patterns and produce a markdown rule delta suggestion.
    Groups corrections by field and identifies the most common model→reviewer pairs.
    """
    if not edits:
        return "# Proposed Rule Delta\n\nNo field edits found in feedback log.\n"

    lines = ["# Proposed Rule Delta\n",
             "Review and apply these rule additions to `skills/classify_opportunities.md`.\n"]

    by_field: dict[str, list] = {}
    for edit in edits:
        f = edit.get("field", "unknown")
        by_field.setdefault(f, []).append(edit)

    for field, field_edits in sorted(by_field.items()):
        lines.append(f"\n## Field: `{field}`\n")
        lines.append(f"Total corrections: {len(field_edits)}\n")
        pairs = Counter(
            (e.get("model_value", ""), e.get("reviewer_value", ""))
            for e in field_edits
        )
        lines.append("\nMost common corrections:\n")
        for (model_val, reviewer_val), count in pairs.most_common(5):
            lines.append(f"- Model said `{model_val}` → Reviewer corrected to `{reviewer_val}` ({count}x)\n")

        # Simple rule suggestion
        most_common_correction = pairs.most_common(1)
        if most_common_correction:
            (mv, rv), _ = most_common_correction[0]
            lines.append(f"\nSuggested rule addition:\n")
            lines.append(f"- When evidence suggests `{rv}`, prefer `{rv}` over `{mv}`\n")

    return "".join(lines)


# ── Promotion ─────────────────────────────────────────────────────────────────

def promote_version(version: str) -> None:
    """
    Apply a staged version to the canonical files.

    Checks that a passing eval report exists before proceeding.
    """
    staging_dir = _STAGING_BASE / version
    if not staging_dir.exists():
        print(f"[promote] Staging directory not found: {staging_dir}")
        return

    # ── Eval gate ────────────────────────────────────────────────────────────
    threshold = float(os.getenv("FEEDBACK_PROMOTION_THRESHOLD", "0.80"))
    eval_dir = Path("output") / "eval"
    passing_report = _find_passing_eval_report(eval_dir, threshold)
    if passing_report is None:
        print(f"[promote] Promotion blocked: no passing eval report found.")
        print(f"  Run --mode eval first. Current threshold: {threshold:.0%}.")
        return

    # ── Append examples to eval dataset ──────────────────────────────────────
    proposed_examples = staging_dir / "proposed_examples.jsonl"
    if proposed_examples.exists():
        _EVAL_EXAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
        added = 0
        with open(_EVAL_EXAMPLES_PATH, "a", encoding="utf-8") as f_out:
            for line in proposed_examples.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    f_out.write(line + "\n")
                    added += 1
        print(f"[promote] {added} examples appended to {_EVAL_EXAMPLES_PATH}")

    # ── Append rule delta to classify skill ──────────────────────────────────
    proposed_rules = staging_dir / "proposed_rules.md"
    if proposed_rules.exists() and _CLASSIFY_SKILL.exists():
        delta = proposed_rules.read_text(encoding="utf-8")
        with open(_CLASSIFY_SKILL, "a", encoding="utf-8") as f_skill:
            f_skill.write(f"\n\n---\n## Feedback-Derived Rules ({version})\n\n")
            f_skill.write(delta)
        print(f"[promote] Rule delta appended to {_CLASSIFY_SKILL}")

    # ── Write promoted.yaml ───────────────────────────────────────────────────
    promoted_meta = (
        f"version: {version}\n"
        f"promoted_at: {_now_iso()}\n"
        f"promoted_by: {_get_reviewer_id()}\n"
        f"eval_report: {passing_report}\n"
    )
    (staging_dir / "promoted.yaml").write_text(promoted_meta, encoding="utf-8")
    print(f"[promote] Promotion complete. Commit config/ and skills/ to record the change.")
    print(f"  Staging dir: {staging_dir}")


def _find_passing_eval_report(eval_dir: Path, threshold: float) -> str | None:
    """Return the path of the most recent passing eval report, or None."""
    if not eval_dir.exists():
        return None
    reports = sorted(eval_dir.glob("eval_*.json"), reverse=True)
    for report_path in reports:
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            if data.get("overall_accuracy", 0) >= threshold:
                return str(report_path)
        except Exception:
            continue
    return None
