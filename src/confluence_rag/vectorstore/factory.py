from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from confluence_rag.vectorstore.chroma_store import ChromaVectorStore
from confluence_rag.vectorstore.jsonl_store import JsonlVectorStore
from confluence_rag.vectorstore.types import VectorStore


def make_vectorstore(
    kind: str,
    *,
    persist_dir: Path,
    collection: str,
    args: dict[str, str] | None = None,
) -> VectorStore:
    args = args or {}
    kind = (kind or "").strip()
    if not kind:
        kind = "jsonl"

    kind_lower = kind.lower()
    if kind_lower == "chroma":
        return ChromaVectorStore(persist_dir=persist_dir, collection=collection)
    if kind_lower in {"jsonl", "file", "export"}:
        return JsonlVectorStore(persist_dir=persist_dir, collection=collection)

    if ":" in kind:
        module_name, attr = kind.split(":", 1)
        module = importlib.import_module(module_name)
        factory = getattr(module, attr)
        if not callable(factory):
            raise ValueError(f"Vector store factory is not callable: {kind}")
        obj = factory(persist_dir=persist_dir, collection=collection, **args)
        return obj  # type: ignore[return-value]

    raise ValueError(f"Unknown vector store kind '{kind}'. Use 'chroma', 'jsonl', or 'module:callable'.")


def parse_kv_args(values: list[str] | None) -> dict[str, str]:
    args: dict[str, str] = {}
    for raw in values or []:
        raw = (raw or "").strip()
        if not raw or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        args[key] = value
    return args

