from __future__ import annotations

from pathlib import Path
from typing import Any


class ChromaVectorStore:
    def __init__(self, *, persist_dir: Path, collection: str) -> None:
        try:
            import chromadb  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise ModuleNotFoundError(
                "Missing dependency 'chromadb'. Install with: python -m pip install chromadb"
            ) from exc

        self._persist_dir = persist_dir
        self._chroma_dir = persist_dir / "chroma"
        self._client = chromadb.PersistentClient(path=str(self._chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def persist_dir(self) -> Path:
        return self._persist_dir

    def delete_page(self, page_id: str) -> None:
        # Chroma raises if no matches; ignore.
        try:
            self._collection.delete(where={"confluence_page_id": page_id})
        except Exception:
            return

    def add_chunks(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        self._collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
