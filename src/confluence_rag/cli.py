from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from confluence_rag.confluence.client import ConfluenceAuth, ConfluenceClient
from confluence_rag.ingest.pipeline import ingest
from confluence_rag.rag.answer import answer_question
from confluence_rag.settings import Settings
from confluence_rag.vectorstore.chroma_store import ChromaVectorStore


app = typer.Typer(add_completion=False, help="Ingest Confluence pages into a vector store and run RAG queries.")
confluence_app = typer.Typer(add_completion=False, help="Confluence connectivity helpers.")
app.add_typer(confluence_app, name="confluence")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _make_confluence(settings: Settings) -> ConfluenceClient:
    auth = ConfluenceAuth(
        mode=settings.confluence.auth_mode,
        token=settings.confluence.token,
        username=settings.confluence.username,
    )
    return ConfluenceClient(
        site_base_url=settings.confluence.base_url,
        auth=auth,
        verify_ssl=settings.confluence.verify_ssl,
    )


def _make_vectorstore(settings: Settings) -> ChromaVectorStore:
    settings.vectorstore.persist_dir.mkdir(parents=True, exist_ok=True)
    return ChromaVectorStore(persist_dir=settings.vectorstore.persist_dir, collection=settings.vectorstore.collection)


@app.command("ingest")
def ingest_cmd(
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    auth: Annotated[str | None, typer.Option("--auth", help="bearer|basic")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    token: Annotated[str | None, typer.Option("--token")] = None,
    verify_ssl: Annotated[bool | None, typer.Option("--verify-ssl/--no-verify-ssl")] = None,
    index_dir: Annotated[Path | None, typer.Option("--index-dir")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    embeddings_provider: Annotated[str | None, typer.Option("--embeddings-provider", help="ollama|openai")] = None,
    embeddings_model: Annotated[str | None, typer.Option("--embeddings-model")] = None,
    llm_provider: Annotated[str | None, typer.Option("--llm-provider", help="ollama|openai|none")] = None,
    llm_model: Annotated[str | None, typer.Option("--llm-model")] = None,
    openai_api_key: Annotated[str | None, typer.Option("--openai-api-key")] = None,
    ollama_base_url: Annotated[str | None, typer.Option("--ollama-base-url")] = None,
    space: Annotated[list[str] | None, typer.Option("--space", help="Space key (repeatable)")] = None,
    label: Annotated[list[str] | None, typer.Option("--label", help="Label (repeatable)")] = None,
    ancestor: Annotated[list[str] | None, typer.Option("--ancestor", help="Ancestor page ID (repeatable)")] = None,
    cql: Annotated[str | None, typer.Option("--cql", help="Raw CQL; overrides space/label/ancestor")] = None,
    page_id: Annotated[list[str] | None, typer.Option("--page-id", help="Page ID (repeatable)")] = None,
    url: Annotated[list[str] | None, typer.Option("--url", help="Page URL (repeatable)")] = None,
    include_archived: Annotated[bool, typer.Option("--include-archived")] = False,
    chunk_size: Annotated[int, typer.Option("--chunk-size")] = 2000,
    chunk_overlap: Annotated[int, typer.Option("--chunk-overlap")] = 200,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """
    Pull Confluence pages and upsert them into the local vector index.
    """
    _configure_logging(verbose)
    console = Console()

    settings = Settings.from_env(
        base_url=base_url,
        auth_mode=auth,
        token=token,
        username=username,
        verify_ssl=verify_ssl,
        persist_dir=index_dir,
        collection=collection,
        embeddings_provider=embeddings_provider,
        embeddings_model=embeddings_model,
        llm_provider=llm_provider or "none",
        llm_model=llm_model,
        openai_api_key=openai_api_key,
        ollama_base_url=ollama_base_url,
    )

    confluence = _make_confluence(settings)
    try:
        vectorstore = _make_vectorstore(settings)
        stats = ingest(
            confluence=confluence,
            vectorstore=vectorstore,
            embeddings_settings=settings.embeddings,
            urls=url,
            page_ids=page_id,
            cql=cql,
            spaces=space,
            labels=label,
            ancestors=ancestor,
            include_archived=include_archived,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            dry_run=dry_run,
            console=console,
        )
    finally:
        confluence.close()

    console.print(
        f"[green]Done.[/green] pages_seen={stats.pages_seen} pages_indexed={stats.pages_indexed} "
        f"pages_skipped={stats.pages_skipped} chunks_written={stats.chunks_written}"
    )


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Question to answer")],
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    auth: Annotated[str | None, typer.Option("--auth", help="bearer|basic")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    token: Annotated[str | None, typer.Option("--token")] = None,
    verify_ssl: Annotated[bool | None, typer.Option("--verify-ssl/--no-verify-ssl")] = None,
    index_dir: Annotated[Path | None, typer.Option("--index-dir")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    embeddings_provider: Annotated[str | None, typer.Option("--embeddings-provider", help="ollama|openai")] = None,
    embeddings_model: Annotated[str | None, typer.Option("--embeddings-model")] = None,
    llm_provider: Annotated[str | None, typer.Option("--llm-provider", help="ollama|openai|none")] = None,
    llm_model: Annotated[str | None, typer.Option("--llm-model")] = None,
    openai_api_key: Annotated[str | None, typer.Option("--openai-api-key")] = None,
    ollama_base_url: Annotated[str | None, typer.Option("--ollama-base-url")] = None,
    top_k: Annotated[int, typer.Option("--top-k")] = 6,
    filter_space: Annotated[str | None, typer.Option("--filter-space", help="Only retrieve from this space key")] = None,
    filter_page_id: Annotated[str | None, typer.Option("--filter-page-id", help="Only retrieve from this page id")] = None,
    show_chunks: Annotated[bool, typer.Option("--show-chunks")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    _configure_logging(verbose)
    console = Console()

    settings = Settings.from_env(
        require_confluence=False,
        base_url=base_url,
        auth_mode=auth,
        token=token,
        username=username,
        verify_ssl=verify_ssl,
        persist_dir=index_dir,
        collection=collection,
        embeddings_provider=embeddings_provider,
        embeddings_model=embeddings_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
        openai_api_key=openai_api_key,
        ollama_base_url=ollama_base_url,
    )

    vectorstore = _make_vectorstore(settings)
    where: dict[str, Any] | None = None
    if filter_space or filter_page_id:
        where = {}
        if filter_space:
            where["confluence_space_key"] = filter_space
        if filter_page_id:
            where["confluence_page_id"] = filter_page_id

    result = answer_question(
        question=question,
        vectorstore=vectorstore,
        embeddings_settings=settings.embeddings,
        llm_settings=settings.llm,
        top_k=top_k,
        where=where,
    )

    console.print(result.answer)

    if result.retrieved:
        console.print("\n[bold]Sources[/bold]")
        for idx, chunk in enumerate(result.retrieved, start=1):
            meta = chunk.metadata or {}
            title = meta.get("confluence_title") or "Untitled"
            url_val = meta.get("confluence_url") or ""
            console.print(f"[{idx}] {title} {url_val}")
            if show_chunks:
                console.print(chunk.text)
                console.print()


@confluence_app.command("spaces")
def confluence_spaces(
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    auth: Annotated[str | None, typer.Option("--auth", help="bearer|basic")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    token: Annotated[str | None, typer.Option("--token")] = None,
    verify_ssl: Annotated[bool | None, typer.Option("--verify-ssl/--no-verify-ssl")] = None,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    _configure_logging(verbose)
    console = Console()

    # Force providers that don't require extra keys for this command.
    settings = Settings.from_env(
        base_url=base_url,
        auth_mode=auth,
        token=token,
        username=username,
        verify_ssl=verify_ssl,
        embeddings_provider="ollama",
        llm_provider="none",
    )
    confluence = _make_confluence(settings)
    try:
        for space in confluence.list_spaces():
            console.print(f'{space.get("key")}\t{space.get("name")}')
    finally:
        confluence.close()


@app.command()
def doctor(
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    auth: Annotated[str | None, typer.Option("--auth", help="bearer|basic")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    token: Annotated[str | None, typer.Option("--token")] = None,
    verify_ssl: Annotated[bool | None, typer.Option("--verify-ssl/--no-verify-ssl")] = None,
    index_dir: Annotated[Path | None, typer.Option("--index-dir")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    embeddings_provider: Annotated[str | None, typer.Option("--embeddings-provider", help="ollama|openai")] = None,
    embeddings_model: Annotated[str | None, typer.Option("--embeddings-model")] = None,
    llm_provider: Annotated[str | None, typer.Option("--llm-provider", help="ollama|openai|none")] = None,
    llm_model: Annotated[str | None, typer.Option("--llm-model")] = None,
    openai_api_key: Annotated[str | None, typer.Option("--openai-api-key")] = None,
    ollama_base_url: Annotated[str | None, typer.Option("--ollama-base-url")] = None,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    _configure_logging(verbose)
    console = Console()

    settings = Settings.from_env(
        base_url=base_url,
        auth_mode=auth,
        token=token,
        username=username,
        verify_ssl=verify_ssl,
        persist_dir=index_dir,
        collection=collection,
        embeddings_provider=embeddings_provider,
        embeddings_model=embeddings_model,
        llm_provider=llm_provider or "none",
        llm_model=llm_model,
        openai_api_key=openai_api_key,
        ollama_base_url=ollama_base_url,
    )

    console.print("[bold]Confluence[/bold]")
    confluence = _make_confluence(settings)
    try:
        first = next(iter(confluence.list_spaces(limit=1)), None)
        if first:
            console.print(f"OK: can list spaces (example: {first.get('key')})")
        else:
            console.print("OK: can list spaces (none returned)")
    finally:
        confluence.close()

    console.print("\n[bold]Vector store[/bold]")
    vs = _make_vectorstore(settings)
    console.print(f"OK: {vs.persist_dir}")

    console.print("\n[bold]Embeddings[/bold]")
    if settings.embeddings.provider == "ollama":
        console.print(f"Configured: Ollama {settings.embeddings.model} ({settings.embeddings.ollama_base_url})")
    else:
        console.print(f"Configured: OpenAI {settings.embeddings.model}")

    console.print("\n[bold]LLM[/bold]")
    if settings.llm.provider == "none":
        console.print("Configured: none")
    elif settings.llm.provider == "ollama":
        console.print(f"Configured: Ollama {settings.llm.model} ({settings.llm.ollama_base_url})")
    else:
        console.print(f"Configured: OpenAI {settings.llm.model}")
