from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup


_PLAIN_TEXT_BODY_RE = re.compile(
    r"<ac:plain-text-body><!\\[CDATA\\[(?P<code>.*?)\\]\\]></ac:plain-text-body>", re.DOTALL
)


def confluence_storage_to_text(storage_html: str) -> str:
    if not storage_html:
        return ""

    def _replace_code(match: re.Match[str]) -> str:
        code = match.group("code")
        return f"<pre>{html.escape(code)}</pre>"

    normalized = _PLAIN_TEXT_BODY_RE.sub(_replace_code, storage_html)
    soup = BeautifulSoup(normalized, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text("\n")
    lines = [line.rstrip() for line in text.splitlines()]

    cleaned: list[str] = []
    blank_streak = 0
    for line in lines:
        if not line.strip():
            blank_streak += 1
            if blank_streak <= 1:
                cleaned.append("")
            continue
        blank_streak = 0
        cleaned.append(line)

    return "\n".join(cleaned).strip()

