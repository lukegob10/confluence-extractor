from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestionState:
    path: Path
    page_versions: dict[str, int]

    @classmethod
    def load(cls, path: Path) -> "IngestionState":
        if not path.exists():
            return cls(path=path, page_versions={})
        data = json.loads(path.read_text(encoding="utf-8"))
        page_versions_raw = data.get("page_versions") or {}
        page_versions: dict[str, int] = {}
        for k, v in page_versions_raw.items():
            try:
                page_versions[str(k)] = int(v)
            except (TypeError, ValueError):
                continue
        return cls(path=path, page_versions=page_versions)

    def get_version(self, page_id: str) -> int | None:
        return self.page_versions.get(page_id)

    def set_version(self, page_id: str, version: int) -> None:
        self.page_versions[page_id] = int(version)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"page_versions": self.page_versions}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

