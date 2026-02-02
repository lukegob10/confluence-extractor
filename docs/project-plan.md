# Confluence Scraper + RAG — Project Plan

## Objective
Build a Python CLI that can:
1) Pull Confluence pages (by URL, page IDs, space(s), labels, ancestor page, or raw CQL),
2) Convert page bodies into clean text,
3) Chunk + embed the text,
4) Persist it in a local vector store,
5) Answer questions using retrieval‑augmented generation (RAG) with source citations.

## Scope (v1)
### In scope
- Confluence page ingestion
  - Select pages by:
    - `--url` (page URL(s))
    - `--page-id` (one or more)
    - `--space` (one or more space keys)
    - `--ancestor` (page tree root(s))
    - `--label` (one or more labels)
    - `--cql` (raw Confluence Query Language)
  - Pull page metadata + content (title, id, space, version, updated time, body)
  - Incremental syncing using Confluence page version (skip unchanged pages)
  - Basic observability: progress + clear logs + dry-run mode
- Text processing
  - Convert Confluence storage HTML to readable plain text
  - Keep code blocks (from Confluence `ac:plain-text-body`) as text
  - Chunking with overlap and deterministic chunk IDs
- Vector store
  - Local persistent store (default: Chroma on disk)
  - Store metadata for filtering (space key, page id, title, url, updated time, version)
- Q&A
  - Retrieval with configurable `top_k`
  - Answer generation via pluggable providers (OpenAI or Ollama) with citations

### Out of scope (initially)
- Attachments (PDF/Office), comments, whiteboards, databases
- Permissions mirroring / per-user ACL enforcement
- Bidirectional sync (writes back to Confluence)
- Web UI (CLI only for now)

## Assumptions
- You have a Confluence Personal Access Token (PAT) with permission to read the spaces/pages you want.
- Your token is provided via env var or prompt (never hard-coded).
- The CLI will run locally (WSL/macOS/Linux) and persist a local index directory.

## Architecture
### Data flow
1. **Select pages** (URL/page IDs/spaces/labels/ancestor/CQL)
2. **Fetch pages** via Confluence REST API
3. **Normalize** content to text
4. **Chunk** to fixed size (with overlap)
5. **Embed** chunks (OpenAI or Ollama embeddings)
6. **Upsert** into vector store (Chroma), deleting old chunks for updated pages
7. **Query**: embed question → vector search → LLM answer with sources

### Storage layout
```
index/
  chroma/                 # Chroma persistent store
  ingestion_state.json    # page_id -> version (for incremental sync)
```

### Document schema (per chunk)
- `id`: `"{page_id}:{version}:{chunk_index}"`
- `text`: chunk text
- `metadata`:
  - `confluence_page_id`
  - `confluence_space_key`
  - `confluence_title`
  - `confluence_url`
  - `confluence_version`
  - `updated_at`
  - `chunk_index`

## CLI plan
### Commands
- `confluence-rag ingest`
  - pulls pages based on selectors and updates the vector index
  - supports `--dry-run` to show what would be pulled
- `confluence-rag query "…"`
  - retrieves the most relevant chunks and answers with citations
- `confluence-rag confluence spaces`
  - lists accessible spaces (sanity check)
- `confluence-rag doctor`
  - validates auth + connectivity + index directory

### Global config inputs
- Environment variables (optionally via `.env`)
- CLI flags override env vars

## Reliability & Observability
- Retry/backoff for transient HTTP errors and rate limiting (429)
- Structured logging (INFO default, DEBUG with `--verbose`)
- Clear summary at end of ingest: pages scanned, pages updated, chunks written

## Security
- Secrets via env vars (`CONFLUENCE_TOKEN`, optionally `OPENAI_API_KEY`)
- `.env` in `.gitignore`
- Do not print tokens in logs

## Milestones
### MVP (1–2 sessions)
- Confluence client (auth, pagination)
- Ingest by `--space` / `--cql` / `--page-id` / `--url`
- HTML → text conversion
- Chunk + embed + persist to local Chroma
- Query with “sources” output (even without LLM)

### v1 (next)
- Incremental sync (version-aware) and deletion of stale chunks
- Filters on query (space/page)
- Better text cleanup for Confluence macros/code blocks
- Add tests for URL parsing + chunking + CQL builder

### v2 (later)
- Attachments ingestion (PDF, docx) + OCR as needed
- Permission-aware indexing (ACL filtering)
- Scheduling / continuous sync

## Clarifying questions (please answer)
1. Confluence type: **Cloud** (atlassian.net) or **Server/Data Center** (self-hosted)?
2. Auth details: does your PAT work with **Bearer** auth, or do you need **Basic** (email/username + token)?
3. Base URL: what is your Confluence base URL (e.g. `https://your-domain.atlassian.net/wiki`)?
4. Scope: do you want ingestion across **all spaces you can access**, or only a defined allowlist?
5. Selection: should “by URL” support **single page**, **page + descendants**, or both?
6. Update model: is “incremental by version number” enough, or do you need delete detection for removed pages too?
7. Vector store preference: local (**Chroma/FAISS**) or remote (**Qdrant/Pinecone/Weaviate**)?
8. Model preference: do you want to use **OpenAI**, **Ollama (local)**, or something else for embeddings + answers?
9. Output: should answers include **inline citations** and a **sources section** with URLs?
10. Size: roughly how many pages / total size are you indexing (10s, 100s, 10k+)?

