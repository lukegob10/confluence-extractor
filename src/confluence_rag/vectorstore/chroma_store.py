from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]
    distance: float | None


class ChromaVectorStore:
    def __init__(self, *, persist_dir: Path, collection: str) -> None:
        try:
            import chromadb  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise ModuleNotFoundError(
                "Missing dependency 'chromadb'. Install with: python3 -m pip install chromadb"
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

    def query(
        self,
        *,
        embedding: list[float],
        top_k: int = 6,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        include = ["documents", "metadatas", "distances"]
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where or None,
            include=include,
        )
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append(RetrievedChunk(text=doc, metadata=meta or {}, distance=dist))
        return chunks
