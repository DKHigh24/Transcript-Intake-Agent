"""
transcript_chunker.py
Parses cleaned paragraphs into speaker turns, keyword-filters relevant turns,
and packs them into token-safe chunks for the extraction step.

Output: list of chunk dicts saved to output/transcript_chunks.json
"""

import json
import re
from pathlib import Path


# Keywords that signal a potentially relevant AI opportunity
CANDIDATE_KEYWORDS = [
    # AI tools / platforms
    "copilot", "chatgpt", "claude", "openai", "anthropic", "gpt",
    "ai", "agent", "automation", "automate", "automated",
    "llm", "model", "prompt", "skill", "workflow",
    # Actions that suggest use cases
    "generate", "summarize", "classify", "extract", "analyze",
    "triage", "detect", "predict", "recommend", "parse",
    "create record", "update record", "trigger", "notify",
    # Pain points / signals
    "manual", "tedious", "time consuming", "bottleneck", "pain point",
    "issue", "problem", "challenge", "risk", "concern",
    "access", "license", "token", "cost", "governance",
    # Org-specific signals
    "knowledge base", "kb", "demo", "intake", "sharepoint",
    "power automate", "power bi", "ado", "smartsheet",
    "release note", "documentation", "transcript",
    "pilot", "reusable", "standard work",
]

# Max characters per chunk (approximate; well below token limits)
# The Copilot SDK and OpenAI both handle ~3 000 chars comfortably.
# Individual turns larger than this are hard-split by sentence to stay under the limit.
MAX_CHUNK_CHARS = 3000


def _text_is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in CANDIDATE_KEYWORDS)


def _build_speaker_turns(cleaned_paragraphs: list[dict]) -> list[dict]:
    """
    Merge consecutive paragraphs by the same speaker into turns.
    Non-speaker paragraphs are included as continuation of the last turn.
    """
    turns = []
    current: dict | None = None

    for para in cleaned_paragraphs:
        if para["is_speaker_turn"]:
            if current:
                turns.append(current)
            current = {
                "speaker": para["speaker"],
                "timestamp": para["timestamp"],
                "text": para["cleaned_text"],
                "paragraph_indices": [para["paragraph_index"]],
            }
        else:
            if current:
                current["text"] += " " + para["cleaned_text"]
                current["paragraph_indices"].append(para["paragraph_index"])
            else:
                # Pre-speaker content (e.g., header, title)
                turns.append({
                    "speaker": None,
                    "timestamp": None,
                    "text": para["cleaned_text"],
                    "paragraph_indices": [para["paragraph_index"]],
                })

    if current:
        turns.append(current)

    return turns


def _filter_relevant_turns(turns: list[dict]) -> list[dict]:
    return [t for t in turns if _text_is_relevant(t["text"])]


def _split_large_turn(turn: dict) -> list[dict]:
    """
    Split a turn whose text exceeds MAX_CHUNK_CHARS into smaller pseudo-turns,
    breaking on sentence boundaries where possible.
    """
    text = turn["text"]
    if len(text) <= MAX_CHUNK_CHARS:
        return [turn]

    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts: list[dict] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > MAX_CHUNK_CHARS:
            parts.append({**turn, "text": current.strip()})
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence
    if current:
        parts.append({**turn, "text": current.strip()})
    return parts


def _pack_chunks(relevant_turns: list[dict]) -> list[dict]:
    """
    Pack relevant turns into chunks under MAX_CHUNK_CHARS.
    Oversized single turns are split before packing.
    """
    # Expand any turns that individually exceed the limit
    expanded: list[dict] = []
    for turn in relevant_turns:
        expanded.extend(_split_large_turn(turn))

    chunks = []
    current_chunk_turns: list[dict] = []
    current_chars = 0

    for turn in expanded:
        turn_len = len(turn["text"])
        if current_chunk_turns and current_chars + turn_len > MAX_CHUNK_CHARS:
            chunks.append(_make_chunk(current_chunk_turns, len(chunks)))
            current_chunk_turns = []
            current_chars = 0
        current_chunk_turns.append(turn)
        current_chars += turn_len

    if current_chunk_turns:
        chunks.append(_make_chunk(current_chunk_turns, len(chunks)))

    return chunks


def _make_chunk(turns: list[dict], index: int) -> dict:
    lines = []
    for t in turns:
        prefix = f"{t['speaker']} [{t['timestamp']}]:" if t["speaker"] and t["timestamp"] else \
                 f"{t['speaker']}:" if t["speaker"] else ""
        lines.append(f"{prefix} {t['text']}".strip())
    return {
        "chunk_index": index,
        "turn_count": len(turns),
        "char_count": sum(len(t["text"]) for t in turns),
        "speakers": list({t["speaker"] for t in turns if t["speaker"]}),
        "text": "\n\n".join(lines),
    }


def chunk_transcript(
    cleaned_paragraphs: list[dict],
    output_path: str = "output/transcript_chunks.json",
) -> list[dict]:
    """
    Full chunking pipeline. Returns chunks and writes output JSON.
    """
    turns = _build_speaker_turns(cleaned_paragraphs)
    relevant = _filter_relevant_turns(turns)
    chunks = _pack_chunks(relevant)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(chunks, indent=2), encoding="utf-8")

    print(f"[chunker] {len(turns)} turns -> {len(relevant)} relevant -> {len(chunks)} chunks -> {output_path}")
    return chunks
