from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env(key: str) -> str | None:
    value = os.getenv(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_bool(key: str, default: bool) -> bool:
    value = _env(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_prefixed(prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        suffix = key[len(prefix) :].strip()
        if not suffix:
            continue
        # VECTORSTORE_ARG_URL -> url
        result[suffix.lower()] = value
    return result


def _parse_kv_pairs(pairs: list[str]) -> dict[str, str]:
    args: dict[str, str] = {}
    for raw in pairs:
        raw = (raw or "").strip()
        if not raw or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        args[k] = v
    return args


def _split_pairs_blob(blob: str | None) -> list[str]:
    if not blob:
        return []
    parts = re.split(r"[,\n;]+", blob)
    return [p.strip() for p in parts if p.strip()]


@dataclass(frozen=True)
class ConfluenceSettings:
    base_url: str
    auth_mode: str  # bearer | basic
    token: str
    username: str | None
    verify_ssl: bool = True


@dataclass(frozen=True)
class VectorStoreSettings:
    kind: str  # chroma | jsonl | module:callable
    persist_dir: Path
    collection: str
    args: dict[str, str]


@dataclass(frozen=True)
class EmbeddingsSettings:
    provider: str  # openai | ollama
    model: str
    openai_api_key: str | None
    ollama_base_url: str


@dataclass(frozen=True)
class Settings:
    confluence: ConfluenceSettings
    vectorstore: VectorStoreSettings
    embeddings: EmbeddingsSettings

    @staticmethod
    def load_dotenv() -> None:
        load_dotenv(override=False)

    @classmethod
    def from_env(
        cls,
        *,
        require_confluence: bool = True,
        base_url: str | None = None,
        auth_mode: str | None = None,
        token: str | None = None,
        username: str | None = None,
        verify_ssl: bool | None = None,
        vectorstore_kind: str | None = None,
        vectorstore_args: list[str] | None = None,
        persist_dir: Path | None = None,
        collection: str | None = None,
        embeddings_provider: str | None = None,
        embeddings_model: str | None = None,
        openai_api_key: str | None = None,
        ollama_base_url: str | None = None,
    ) -> "Settings":
        cls.load_dotenv()

        base_url = base_url or _env("CONFLUENCE_BASE_URL")
        auth_mode = (auth_mode or _env("CONFLUENCE_AUTH") or "bearer").lower()
        token = token or _env("CONFLUENCE_TOKEN")
        username = username or _env("CONFLUENCE_USERNAME")
        verify_ssl = verify_ssl if verify_ssl is not None else _env_bool("CONFLUENCE_VERIFY_SSL", True)

        persist_dir = persist_dir or Path(_env("VECTORSTORE_DIR") or "index")
        collection = collection or _env("VECTORSTORE_COLLECTION") or "confluence"
        vectorstore_kind = vectorstore_kind or _env("VECTORSTORE") or _env("VECTORSTORE_KIND") or "jsonl"

        args: dict[str, str] = {}
        args.update(_env_prefixed("VECTORSTORE_ARG_"))
        args.update(_parse_kv_pairs(_split_pairs_blob(_env("VECTORSTORE_ARGS"))))
        args.update(_parse_kv_pairs(vectorstore_args or []))

        embeddings_provider = (embeddings_provider or _env("EMBEDDINGS_PROVIDER") or "ollama").lower()
        embeddings_model = embeddings_model or _env("EMBEDDINGS_MODEL") or "nomic-embed-text"

        openai_api_key = openai_api_key or _env("OPENAI_API_KEY")
        ollama_base_url = ollama_base_url or _env("OLLAMA_BASE_URL") or "http://localhost:11434"

        if require_confluence:
            if not base_url:
                raise ValueError("Missing Confluence base URL (set CONFLUENCE_BASE_URL or pass --base-url).")
            if not token:
                raise ValueError("Missing Confluence token (set CONFLUENCE_TOKEN or pass --token).")
            if auth_mode not in {"bearer", "basic"}:
                raise ValueError("CONFLUENCE_AUTH/--auth must be 'bearer' or 'basic'.")
            if auth_mode == "basic" and not username:
                raise ValueError("Basic auth requires CONFLUENCE_USERNAME/--username.")
        else:
            base_url = base_url or "http://unused.local"
            token = token or "unused"
            if auth_mode not in {"bearer", "basic"}:
                auth_mode = "bearer"
        if embeddings_provider not in {"openai", "ollama"}:
            raise ValueError("EMBEDDINGS_PROVIDER/--embeddings-provider must be 'openai' or 'ollama'.")
        if embeddings_provider == "openai" and not openai_api_key:
            raise ValueError("OpenAI embeddings requires OPENAI_API_KEY.")

        confluence = ConfluenceSettings(
            base_url=base_url,
            auth_mode=auth_mode,
            token=token,
            username=username,
            verify_ssl=verify_ssl,
        )
        vectorstore = VectorStoreSettings(
            kind=vectorstore_kind,
            persist_dir=persist_dir,
            collection=collection,
            args=args,
        )
        embeddings = EmbeddingsSettings(
            provider=embeddings_provider,
            model=embeddings_model,
            openai_api_key=openai_api_key,
            ollama_base_url=ollama_base_url,
        )
        return cls(confluence=confluence, vectorstore=vectorstore, embeddings=embeddings)
