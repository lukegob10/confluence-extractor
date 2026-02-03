from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from confluence_rag.confluence.client import ConfluenceClient
from confluence_rag.confluence.models import ConfluencePage
from confluence_rag.confluence.text import confluence_storage_to_text
from confluence_rag.confluence.url import page_id_from_url
from confluence_rag.ingest.chunker import chunk_text
from confluence_rag.ingest.selectors import build_cql
from confluence_rag.providers.ollama import OllamaEmbeddings
from confluence_rag.providers.openai import OpenAIEmbeddings
from confluence_rag.settings import EmbeddingsSettings
from confluence_rag.state import IngestionState
from confluence_rag.vectorstore.types import VectorStore


@dataclass(frozen=True)
class IngestStats:
    pages_seen: int = 0
    pages_skipped: int = 0
    pages_indexed: int = 0
    chunks_written: int = 0


def _iter_pages(
    confluence: ConfluenceClient,
    *,
    urls: list[str] | None,
    page_ids: list[str] | None,
    cql: str | None,
    spaces: list[str] | None,
    labels: list[str] | None,
    ancestors: list[str] | None,
    include_archived: bool,
) -> tuple[Iterable[ConfluencePage], str | None]:
    ids: list[str] = []
    for page_id in page_ids or []:
        page_id = (page_id or "").strip()
        if page_id:
            ids.append(page_id)
    for url in urls or []:
        pid = page_id_from_url(url)
        if pid:
            ids.append(pid)

    if ids:
        def _gen() -> Iterable[ConfluencePage]:
            for pid in ids:
                yield confluence.get_page(pid)

        return _gen(), None

    effective_cql = cql.strip() if cql else build_cql(
        spaces=spaces, labels=labels, ancestors=ancestors, include_archived=include_archived
    )
    return confluence.search_pages(cql=effective_cql), effective_cql


def _make_embeddings(settings: EmbeddingsSettings):
    if settings.provider == "openai":
        assert settings.openai_api_key
        return OpenAIEmbeddings(api_key=settings.openai_api_key, model=settings.model)
    if settings.provider == "ollama":
        return OllamaEmbeddings(base_url=settings.ollama_base_url, model=settings.model)
    raise ValueError(f"Unsupported embeddings provider: {settings.provider}")


def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def ingest(
    *,
    confluence: ConfluenceClient,
    vectorstore: VectorStore,
    embeddings_settings: EmbeddingsSettings,
    urls: list[str] | None = None,
    page_ids: list[str] | None = None,
    cql: str | None = None,
    spaces: list[str] | None = None,
    labels: list[str] | None = None,
    ancestors: list[str] | None = None,
    include_archived: bool = False,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
    dry_run: bool = False,
    console: Console | None = None,
) -> IngestStats:
    console = console or Console()

    state_path = Path(vectorstore.persist_dir) / "ingestion_state.json"
    state = IngestionState.load(state_path)

    pages, effective_cql = _iter_pages(
        confluence,
        urls=urls,
        page_ids=page_ids,
        cql=cql,
        spaces=spaces,
        labels=labels,
        ancestors=ancestors,
        include_archived=include_archived,
    )
    if effective_cql:
        console.print(f"[dim]CQL:[/dim] {effective_cql}")

    stats = IngestStats()
    embeddings = _make_embeddings(embeddings_settings)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task("Ingesting pages", total=None)
        for page in pages:
            stats = IngestStats(
                pages_seen=stats.pages_seen + 1,
                pages_skipped=stats.pages_skipped,
                pages_indexed=stats.pages_indexed,
                chunks_written=stats.chunks_written,
            )
            progress.update(task_id, description=f"Ingesting: {page.title[:70]}")

            if page.version is not None:
                prev_version = state.get_version(page.id)
                if prev_version is not None and page.version <= prev_version:
                    stats = IngestStats(
                        pages_seen=stats.pages_seen,
                        pages_skipped=stats.pages_skipped + 1,
                        pages_indexed=stats.pages_indexed,
                        chunks_written=stats.chunks_written,
                    )
                    continue

            if dry_run:
                console.print(f"{page.id}\t{page.space_key or ''}\t{page.title}")
                continue

            text = confluence_storage_to_text(page.body_storage)
            if not text.strip():
                stats = IngestStats(
                    pages_seen=stats.pages_seen,
                    pages_skipped=stats.pages_skipped + 1,
                    pages_indexed=stats.pages_indexed,
                    chunks_written=stats.chunks_written,
                )
                continue

            chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if not chunks:
                stats = IngestStats(
                    pages_seen=stats.pages_seen,
                    pages_skipped=stats.pages_skipped + 1,
                    pages_indexed=stats.pages_indexed,
                    chunks_written=stats.chunks_written,
                )
                continue

            all_embeddings: list[list[float]] = []
            for batch in _batched(chunks, batch_size=64):
                all_embeddings.extend(embeddings.embed_texts(batch))

            vectorstore.delete_page(page.id)
            ids: list[str] = []
            metadatas: list[dict] = []
            for idx, chunk in enumerate(chunks):
                ids.append(f"{page.id}:{page.version or 0}:{idx}")
                metadatas.append(
                    {
                        "confluence_page_id": page.id,
                        "confluence_space_key": page.space_key,
                        "confluence_title": page.title,
                        "confluence_url": page.url,
                        "confluence_version": page.version,
                        "updated_at": page.updated_at,
                        "embedding_provider": embeddings_settings.provider,
                        "embedding_model": embeddings_settings.model,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "chunk_index": idx,
                    }
                )

            vectorstore.add_chunks(
                ids=ids,
                documents=chunks,
                embeddings=all_embeddings,
                metadatas=metadatas,
            )

            if page.version is not None:
                state.set_version(page.id, page.version)

            stats = IngestStats(
                pages_seen=stats.pages_seen,
                pages_skipped=stats.pages_skipped,
                pages_indexed=stats.pages_indexed + 1,
                chunks_written=stats.chunks_written + len(chunks),
            )

    if not dry_run:
        state.save()

    return stats
