"""
candidate_detector.py
Sends keyword-filtered transcript chunks to the OpenAI model and extracts
candidate AI opportunities. Saves output/candidates.json.

Only relevant chunks are sent — never the full transcript.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from llm_client import call_llm, llm_backend_name

EXTRACTION_SYSTEM_PROMPT = """You are an AI opportunity analyst for the Electronics AI Working Group.

Your job is to identify candidate AI use cases from meeting transcript excerpts.

Extract candidates when the transcript describes:
- AI demos, tools, or workflows (Copilot, ChatGPT, Claude, agents, automations)
- Knowledge base candidates
- Access, licensing, token, or governance issues
- Reusable patterns or standard work
- Survey themes requiring action
- Repeated manual work that AI could reduce

Do NOT extract:
- Greetings, agenda transitions, or casual chat
- One-off comments with no workflow, owner, or next step
- Duplicate mentions of an already-listed candidate
- Vague AI commentary without a process or action

Return ONLY a valid JSON array. No explanation. No markdown fences.

Format:
[
  {
    "candidate_title": "",
    "candidate_summary": "",
    "source_speaker": "",
    "source_timestamp": "",
    "evidence_summary": "",
    "confidence": "High | Medium | Low"
  }
]

Return [] if no valid candidates are found in this chunk."""

EXTRACTION_USER_TEMPLATE = """Transcript chunk {chunk_index} of {total_chunks}:

{chunk_text}

Extract candidate AI opportunities from the above. Return only valid JSON."""


def _call_model(chunk: dict, chunk_index: int, total_chunks: int) -> list[dict]:
    user_msg = EXTRACTION_USER_TEMPLATE.format(
        chunk_index=chunk_index + 1,
        total_chunks=total_chunks,
        chunk_text=chunk["text"],
    )
    raw = call_llm(EXTRACTION_SYSTEM_PROMPT, user_msg)

    # Model may return {"candidates": [...]} or a bare array — normalize
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    # Look for any list value in the response object
    for v in parsed.values():
        if isinstance(v, list):
            return v
    return []


def detect_candidates(
    chunks: list[dict],
    output_path: str = "output/candidates.json",
) -> list[dict]:
    """
    Run extraction over all chunks. Returns deduplicated candidate list.
    """
    print(f"[extractor] backend: {llm_backend_name()}")
    all_candidates: list[dict] = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        print(f"[extractor] chunk {i+1}/{total} ({chunk['char_count']} chars, {chunk['turn_count']} turns)...")
        try:
            candidates = _call_model(chunk, i, total)
            print(f"  -> {len(candidates)} candidate(s) found")
            all_candidates.extend(candidates)
        except Exception as e:
            print(f"  [warn] chunk {i+1} failed: {e}")

    # Light deduplication: drop exact title matches (case-insensitive)
    seen_titles: set[str] = set()
    deduped: list[dict] = []
    for c in all_candidates:
        key = c.get("candidate_title", "").strip().lower()
        if key and key not in seen_titles:
            seen_titles.add(key)
            deduped.append(c)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(deduped, indent=2), encoding="utf-8")

    print(f"[extractor] {len(all_candidates)} total -> {len(deduped)} after dedup -> {output_path}")
    return deduped
