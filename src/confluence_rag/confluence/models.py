from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfluencePage:
    id: str
    title: str
    space_key: str | None
    url: str | None
    version: int | None
    updated_at: str | None
    body_storage: str

