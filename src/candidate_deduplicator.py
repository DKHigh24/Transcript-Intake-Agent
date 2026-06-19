"""
candidate_deduplicator.py

Within-session fuzzy deduplication of extracted candidates.

After the LLM extractor runs across multiple chunks of the same transcript,
the same idea can surface 2–4 times with slightly different wording. This
module collapses near-duplicates into the strongest representative candidate
before classification, reducing noise and LLM cost.

Algorithm:
  - Compare every pair of candidates on combined (title + evidence_summary) text
  - Use difflib.SequenceMatcher ratio as the similarity metric
  - Pairs above `threshold` are merged: keep the candidate with the longer
    evidence_summary; discard the other
  - Repeat until no more pairs exceed the threshold (handles chains)
  - Log discarded candidates at DEBUG level with their similarity score
"""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _similarity(a: dict, b: dict) -> float:
    """Return similarity ratio for two candidates based on title + evidence text."""
    text_a = f"{a.get('candidate_title', '')} {a.get('evidence_summary', '')}".lower().strip()
    text_b = f"{b.get('candidate_title', '')} {b.get('evidence_summary', '')}".lower().strip()
    return SequenceMatcher(None, text_a, text_b).ratio()


def _pick_winner(a: dict, b: dict) -> tuple[dict, dict]:
    """Return (keeper, discard): prefer the candidate with longer evidence_summary."""
    len_a = len(a.get("evidence_summary") or "")
    len_b = len(b.get("evidence_summary") or "")
    if len_b > len_a:
        return b, a
    return a, b


def deduplicate_candidates(candidates: list[dict], threshold: float = 0.72) -> list[dict]:
    """
    Merge near-duplicate candidates within a single session.

    Args:
        candidates: List of extracted candidate dicts from candidate_detector.
        threshold:  Similarity ratio above which two candidates are considered
                    duplicates (default 0.72).

    Returns:
        Deduplicated list — always a subset of the input.
    """
    if len(candidates) <= 1:
        return candidates

    # Work on a mutable copy; use index-based removal to preserve order
    remaining = list(candidates)
    changed = True

    while changed:
        changed = False
        merged = []
        skip = set()

        for i in range(len(remaining)):
            if i in skip:
                continue
            for j in range(i + 1, len(remaining)):
                if j in skip:
                    continue
                sim = _similarity(remaining[i], remaining[j])
                if sim >= threshold:
                    keeper, discard = _pick_winner(remaining[i], remaining[j])
                    logger.debug(
                        "[dedup] merged (%.2f sim): '%s' <- discarded '%s'",
                        sim,
                        keeper.get("candidate_title", "?")[:60],
                        discard.get("candidate_title", "?")[:60],
                    )
                    # Replace i with keeper, mark j for removal
                    remaining[i] = keeper
                    skip.add(j)
                    changed = True

        remaining = [c for idx, c in enumerate(remaining) if idx not in skip]

    return remaining
