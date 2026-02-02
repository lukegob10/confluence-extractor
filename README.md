# Confluence Scraper + RAG (CLI)

This repo contains a Python CLI to ingest Confluence pages into a local vector store and answer questions using RAG.

## Quickstart
1. Create a `.env` file (or export env vars):
   - `CONFLUENCE_BASE_URL` (example: `https://your-domain.atlassian.net/wiki`)
   - `CONFLUENCE_AUTH` (`bearer` or `basic`)
   - `CONFLUENCE_USERNAME` (only for `basic`)
   - `CONFLUENCE_TOKEN`
   - Optional (for OpenAI): `OPENAI_API_KEY`

2. Install:
   - Recommended (virtualenv):
     - `sudo apt-get install -y python3-venv` (Debian/Ubuntu)
     - `python3 -m venv .venv && . .venv/bin/activate`
     - `python3 -m pip install -e '.[dev]'`
   - If you can't use venv (PEP 668), you can also use:
     - `python3 -m pip install --break-system-packages -e '.[dev]'`

3. Ingest:
   - `confluence-rag ingest --space ENG --space OPS`
   - or `confluence-rag ingest --cql 'space=ENG and type=page'`

4. Ask:
   - `confluence-rag query "How do we deploy the service?"`

See `docs/project-plan.md` for detailed requirements and open questions.
