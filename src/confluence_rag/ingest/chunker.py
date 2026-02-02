from __future__ import annotations

import re


def chunk_text(text: str, *, chunk_size: int = 2000, chunk_overlap: int = 200) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be < chunk_size")

    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    step = chunk_size - chunk_overlap
    chunks: list[str] = []

    i = 0
    while i < len(text):
        raw = text[i : i + chunk_size]
        if i + chunk_size < len(text):
            # Try to avoid cutting in the middle of a word by trimming to last whitespace.
            trimmed = re.sub(r"\\s+\\S*$", "", raw)
            if len(trimmed) >= max(200, int(chunk_size * 0.5)):
                raw = trimmed
        chunk = raw.strip()
        if chunk:
            chunks.append(chunk)
        i += step

    # De-dupe rare cases where trimming caused identical adjacent chunks.
    deduped: list[str] = []
    for chunk in chunks:
        if not deduped or deduped[-1] != chunk:
            deduped.append(chunk)
    return deduped

