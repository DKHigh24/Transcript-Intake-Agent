"""
transcript_cleaner.py
Normalizes raw paragraph dicts from transcript_reader.
- Fixes encoding artifacts
- Normalizes whitespace
- Detects and tags speaker turns and timestamps
- Drops empty/noise-only lines
"""

import re
from typing import Optional


# Common timestamp patterns: [00:01:23], 00:01:23, (00:01), 1:23:45
_TIMESTAMP_RE = re.compile(
    r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?"
)

# Speaker line patterns:
#   "John Smith: ..."
#   "John Smith [00:01]: ..."
#   "John Smith (00:01): ..."
#   "JOHN SMITH: ..."
_SPEAKER_RE = re.compile(
    r"^([A-Z][A-Za-z .'\-]+?)(?:\s*[\[\(]\d{1,2}:\d{2}(?::\d{2})?[\]\)])?\s*:\s*(.*)",
    re.DOTALL,
)

# Encoding artifacts to clean
_ARTIFACTS = [
    ("\u2019", "'"),
    ("\u2018", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2013", "-"),
    ("\u2014", "-"),
    ("\u00a0", " "),
    ("\u2026", "..."),
]


def _fix_encoding(text: str) -> str:
    for bad, good in _ARTIFACTS:
        text = text.replace(bad, good)
    return text


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_timestamp(text: str) -> Optional[str]:
    m = _TIMESTAMP_RE.match(text.strip())
    if m:
        return m.group(1)
    return None


def _extract_speaker(text: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Returns (speaker, inline_timestamp, remaining_text).
    """
    m = _SPEAKER_RE.match(text.strip())
    if m:
        speaker = m.group(1).strip()
        body = m.group(2).strip()
        ts = _extract_timestamp(text)
        return speaker, ts, body
    return None, None, text


def clean_paragraphs(paragraphs: list[dict]) -> list[dict]:
    """
    Clean and annotate raw paragraph dicts.

    Each output dict adds:
        cleaned_text, speaker (or None), timestamp (or None), is_speaker_turn.
    """
    cleaned = []
    for para in paragraphs:
        text = _fix_encoding(para["text"])
        text = _normalize_whitespace(text)
        if not text:
            continue

        speaker, ts, body = _extract_speaker(text)
        is_speaker_turn = speaker is not None

        cleaned.append({
            **para,
            "cleaned_text": body if is_speaker_turn else text,
            "speaker": speaker,
            "timestamp": ts,
            "is_speaker_turn": is_speaker_turn,
        })

    return cleaned
