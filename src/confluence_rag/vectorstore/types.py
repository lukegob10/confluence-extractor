from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class VectorStore(Protocol):
    @property
    def persist_dir(self) -> Path: ...

    def delete_page(self, page_id: str) -> None: ...

    def add_chunks(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

