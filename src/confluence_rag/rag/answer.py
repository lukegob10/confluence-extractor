from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from confluence_rag.providers.ollama import OllamaChat, OllamaEmbeddings
from confluence_rag.providers.openai import OpenAIChat, OpenAIEmbeddings
from confluence_rag.settings import EmbeddingsSettings, LLMSettings
from confluence_rag.vectorstore.chroma_store import ChromaVectorStore, RetrievedChunk


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    retrieved: list[RetrievedChunk]


def _make_embeddings(settings: EmbeddingsSettings):
    if settings.provider == "openai":
        assert settings.openai_api_key
        return OpenAIEmbeddings(api_key=settings.openai_api_key, model=settings.model)
    if settings.provider == "ollama":
        return OllamaEmbeddings(base_url=settings.ollama_base_url, model=settings.model)
    raise ValueError(f"Unsupported embeddings provider: {settings.provider}")


def _make_llm(settings: LLMSettings):
    if settings.provider == "none":
        return None
    if settings.provider == "openai":
        assert settings.openai_api_key
        return OpenAIChat(api_key=settings.openai_api_key, model=settings.model)
    if settings.provider == "ollama":
        return OllamaChat(base_url=settings.ollama_base_url, model=settings.model)
    raise ValueError(f"Unsupported LLM provider: {settings.provider}")


def answer_question(
    *,
    question: str,
    vectorstore: ChromaVectorStore,
    embeddings_settings: EmbeddingsSettings,
    llm_settings: LLMSettings,
    top_k: int = 6,
    where: dict[str, Any] | None = None,
) -> AnswerResult:
    embeddings = _make_embeddings(embeddings_settings)
    query_vec = embeddings.embed_texts([question])[0]
    retrieved = vectorstore.query(embedding=query_vec, top_k=top_k, where=where)

    llm = _make_llm(llm_settings)
    if llm is None:
        return AnswerResult(
            answer="LLM disabled (LLM_PROVIDER=none). Showing retrieved chunks only.",
            retrieved=retrieved,
        )

    sources_lines: list[str] = []
    for idx, chunk in enumerate(retrieved, start=1):
        meta = chunk.metadata or {}
        title = meta.get("confluence_title") or "Untitled"
        url = meta.get("confluence_url") or ""
        space = meta.get("confluence_space_key") or ""
        sources_lines.append(f"[{idx}] {title} ({space}) {url}\n{chunk.text}")

    sources_blob = "\n\n".join(sources_lines)
    messages = [
        {
            "role": "system",
            "content": (
                "You answer questions using only the provided Confluence excerpts. "
                "If the excerpts do not contain the answer, say you don't know. "
                "Cite sources with bracket numbers like [1], [2]."
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nSources:\n{sources_blob}",
        },
    ]
    answer = llm.chat(messages=messages, temperature=0.2)
    return AnswerResult(answer=answer.strip(), retrieved=retrieved)

