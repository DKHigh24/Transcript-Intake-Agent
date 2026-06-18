"""
opportunity_matcher.py
Deterministic (no-AI) matching used to recognize when an opportunity extracted in
one week is the same as one tracked from a previous week.

Matching combines:
  - normalized title equality (after slugify),
  - difflib sequence ratio on titles,
  - token (word) overlap (Jaccard) on titles,
ignoring common stop words. This keeps recurrence detection token-friendly and
fully reproducible.
"""

from difflib import SequenceMatcher

from period_utils import slugify

# Words ignored when comparing titles by token overlap.
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "ai", "use", "case", "tool", "tools", "standard", "work", "process",
    "rollout", "general", "new",
}

# Tuning thresholds (kept conservative to avoid false merges).
_RATIO_THRESHOLD = 0.82
_TOKEN_THRESHOLD = 0.60


def _tokens(title: str) -> set[str]:
    return {t for t in slugify(title).split("-") if t and t not in _STOP_WORDS}


def _token_overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def title_similarity(a: str, b: str) -> float:
    """Combined similarity score in [0, 1] between two opportunity titles."""
    if not a or not b:
        return 0.0
    if slugify(a) == slugify(b):
        return 1.0
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    overlap = _token_overlap(a, b)
    return max(ratio, overlap)


def is_match(a: str, b: str) -> bool:
    """True when two titles should be treated as the same opportunity."""
    if slugify(a) == slugify(b):
        return True
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    overlap = _token_overlap(a, b)
    return ratio >= _RATIO_THRESHOLD or overlap >= _TOKEN_THRESHOLD


def stable_key(title: str) -> str:
    """Stable slug key for a brand-new opportunity title."""
    return slugify(title)


def find_match(title: str, entries: list[dict]) -> dict | None:
    """
    Return the best-matching existing history entry for `title`, or None.

    `entries` are history records each having a "title" and optional "aliases".
    The candidate with the highest similarity above threshold wins.
    """
    best: dict | None = None
    best_score = 0.0
    for entry in entries:
        candidates = [entry.get("title", "")] + entry.get("aliases", [])
        score = max((title_similarity(title, c) for c in candidates), default=0.0)
        matched = any(is_match(title, c) for c in candidates if c)
        if matched and score > best_score:
            best = entry
            best_score = score
    return best
