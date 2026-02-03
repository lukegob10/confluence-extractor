from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlVectorStore:
    """
    Lightweight "vector store" exporter.

    Writes one JSONL file per Confluence page containing:
    {id, text, embedding, metadata}

    Location:
      <persist_dir>/jsonl/<collection>/<page_id>.jsonl
    """

    def __init__(self, *, persist_dir: Path, collection: str) -> None:
        self._persist_dir = persist_dir
        self._collection = collection
        self._out_dir = persist_dir / "jsonl" / collection
        self._out_dir.mkdir(parents=True, exist_ok=True)

    @property
    def persist_dir(self) -> Path:
        return self._persist_dir

    def delete_page(self, page_id: str) -> None:
        path = self._out_dir / f"{page_id}.jsonl"
        if path.exists():
            path.unlink()

    def add_chunks(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        if not (len(ids) == len(documents) == len(embeddings) == len(metadatas)):
            raise ValueError("ids/documents/embeddings/metadatas length mismatch")

        page_id = str((metadatas[0] or {}).get("confluence_page_id") or "unknown")
        path = self._out_dir / f"{page_id}.jsonl"

        with path.open("w", encoding="utf-8") as f:
            for chunk_id, doc, emb, meta in zip(ids, documents, embeddings, metadatas):
                record = {"id": chunk_id, "text": doc, "embedding": emb, "metadata": meta}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

