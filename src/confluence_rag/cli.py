from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from confluence_rag.confluence.client import ConfluenceAuth, ConfluenceClient
from confluence_rag.ingest.pipeline import ingest
from confluence_rag.settings import Settings
from confluence_rag.vectorstore.factory import make_vectorstore
from confluence_rag.vectorstore.types import VectorStore


app = typer.Typer(
    add_completion=False,
    help="Collect and preprocess Confluence pages into a vector store.",
)
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


def _make_vectorstore(settings: Settings) -> VectorStore:
    settings.vectorstore.persist_dir.mkdir(parents=True, exist_ok=True)
    return make_vectorstore(
        settings.vectorstore.kind,
        persist_dir=settings.vectorstore.persist_dir,
        collection=settings.vectorstore.collection,
        args=settings.vectorstore.args,
    )


@app.command("ingest")
def ingest_cmd(
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    auth: Annotated[str | None, typer.Option("--auth", help="bearer|basic")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    token: Annotated[str | None, typer.Option("--token")] = None,
    verify_ssl: Annotated[bool | None, typer.Option("--verify-ssl/--no-verify-ssl")] = None,
    vectorstore: Annotated[
        str | None,
        typer.Option("--vectorstore", help="chroma|jsonl|module:callable (see docs)"),
    ] = None,
    vectorstore_arg: Annotated[
        list[str] | None,
        typer.Option("--vectorstore-arg", help="Extra vectorstore args (repeatable) like key=value"),
    ] = None,
    index_dir: Annotated[Path | None, typer.Option("--index-dir")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    embeddings_provider: Annotated[str | None, typer.Option("--embeddings-provider", help="ollama|openai")] = None,
    embeddings_model: Annotated[str | None, typer.Option("--embeddings-model")] = None,
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
    Pull Confluence pages and write embedded chunks to the configured vector store.
    """
    _configure_logging(verbose)
    console = Console()

    settings = Settings.from_env(
        base_url=base_url,
        auth_mode=auth,
        token=token,
        username=username,
        verify_ssl=verify_ssl,
        vectorstore_kind=vectorstore,
        vectorstore_args=vectorstore_arg,
        persist_dir=index_dir,
        collection=collection,
        embeddings_provider=embeddings_provider,
        embeddings_model=embeddings_model,
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
    vectorstore: Annotated[
        str | None,
        typer.Option("--vectorstore", help="chroma|jsonl|module:callable (see docs)"),
    ] = None,
    vectorstore_arg: Annotated[
        list[str] | None,
        typer.Option("--vectorstore-arg", help="Extra vectorstore args (repeatable) like key=value"),
    ] = None,
    index_dir: Annotated[Path | None, typer.Option("--index-dir")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    embeddings_provider: Annotated[str | None, typer.Option("--embeddings-provider", help="ollama|openai")] = None,
    embeddings_model: Annotated[str | None, typer.Option("--embeddings-model")] = None,
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
        vectorstore_kind=vectorstore,
        vectorstore_args=vectorstore_arg,
        persist_dir=index_dir,
        collection=collection,
        embeddings_provider=embeddings_provider,
        embeddings_model=embeddings_model,
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
    console.print(f"Configured: {settings.vectorstore.kind} ({vs.persist_dir})")
    if settings.vectorstore.args:
        console.print(f"Args: {settings.vectorstore.args}")

    console.print("\n[bold]Embeddings[/bold]")
    if settings.embeddings.provider == "ollama":
        console.print(f"Configured: Ollama {settings.embeddings.model} ({settings.embeddings.ollama_base_url})")
    else:
        console.print(f"Configured: OpenAI {settings.embeddings.model}")
