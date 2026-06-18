"""
transcript_reader.py
Reads a .docx transcript and returns a list of paragraph dicts.
Each dict contains: text, style, paragraph_index.
"""

from pathlib import Path
from docx import Document


def read_transcript(docx_path: str) -> list[dict]:
    """
    Read a .docx transcript and return a list of paragraph dicts.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        List of dicts with keys: text, style, paragraph_index.
    """
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {docx_path}")
    if path.suffix.lower() != ".docx":
        raise ValueError(f"Expected a .docx file, got: {path.suffix}")

    doc = Document(str(path))
    paragraphs = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        paragraphs.append({
            "text": text,
            "style": para.style.name if para.style else "",
            "paragraph_index": i,
        })

    return paragraphs
