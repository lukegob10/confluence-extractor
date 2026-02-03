# Confluence Ingestion (CLI)

This repo contains a Python CLI to pull Confluence pages, preprocess/chunk them, generate embeddings, and write them to a pluggable vector store (or export as JSONL). It does **not** do question answering.

## Quickstart
1. Create a `.env` file (or set environment variables):
   - `CONFLUENCE_BASE_URL` (example: `https://your-domain.atlassian.net/wiki`)
   - `CONFLUENCE_AUTH` (`bearer` or `basic`)
   - `CONFLUENCE_USERNAME` (only for `basic`)
   - `CONFLUENCE_TOKEN`
   - Optional (for OpenAI): `OPENAI_API_KEY`
   
   Example `.env`:
   ```dotenv
   CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
   CONFLUENCE_AUTH=bearer
   CONFLUENCE_TOKEN=YOUR_PAT_HERE
   ```

2. Install:
   - PowerShell:
     - `py -3.12 -m venv .venv`
     - `. .\.venv\Scripts\Activate.ps1`
     - `python -m pip install -U pip`
     - `python -m pip install -e ".[dev]"`
   - CMD:
     - `py -3.12 -m venv .venv`
     - `.\\.venv\\Scripts\\activate.bat`
     - `python -m pip install -U pip`
     - `python -m pip install -e ".[dev]"`
   - If PowerShell activation is blocked, either run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` or use `activate.bat`.
   
   If you want the built-in Chroma store, install extras: `python -m pip install -e ".[dev,chroma]"`

3. Ingest:
   - `confluence-ingest ingest --space ENG --space OPS --vectorstore jsonl`
   - PowerShell CQL example: `confluence-ingest ingest --cql 'space=ENG and type=page' --vectorstore jsonl`
   - CMD CQL example: `confluence-ingest ingest --cql "space=ENG and type=page" --vectorstore jsonl`
   - Change embedding model at runtime: `confluence-ingest ingest --embeddings-provider ollama --embeddings-model nomic-embed-text`

   Notes:
   - `confluence-rag` is an alias for `confluence-ingest`.

4. Output:
   - JSONL export: `index\\jsonl\\<collection>\\<page_id>.jsonl`
   - Chroma (if selected): `index\\chroma\\`

See `docs/project-plan.md` for detailed requirements, selectors, and vector store plugin notes.
