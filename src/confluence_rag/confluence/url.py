from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


_CLOUD_PAGES_RE = re.compile(r"/pages/(?P<id>\d+)(/|$)")
_PAGEID_QUERY_RE = re.compile(r"^\d+$")


def page_id_from_url(url: str) -> str | None:
    """
    Best-effort extractor for Confluence page IDs from common URL formats:
    - Cloud:  .../wiki/spaces/SPACE/pages/123456789/Title
    - Server/DC: .../pages/viewpage.action?pageId=123456
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None

    match = _CLOUD_PAGES_RE.search(parsed.path)
    if match:
        return match.group("id")

    qs = parse_qs(parsed.query)
    page_ids = qs.get("pageId") or qs.get("pageid") or qs.get("pageID")
    if page_ids:
        candidate = page_ids[0].strip()
        if _PAGEID_QUERY_RE.match(candidate):
            return candidate

    return None
