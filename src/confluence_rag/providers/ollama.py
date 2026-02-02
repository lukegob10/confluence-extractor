from __future__ import annotations

from typing import Any

import httpx


class OllamaError(RuntimeError):
    pass


class OllamaEmbeddings:
    def __init__(self, *, base_url: str, model: str) -> None:
        self._model = model
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=120.0)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            resp = self._client.post("/api/embeddings", json={"model": self._model, "prompt": text})
            if resp.is_error:
                raise OllamaError(f"Ollama embeddings error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            vec = data.get("embedding")
            if not isinstance(vec, list):
                raise OllamaError("Ollama embeddings returned unexpected format.")
            embeddings.append(vec)
        return embeddings


class OllamaChat:
    def __init__(self, *, base_url: str, model: str) -> None:
        self._model = model
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=300.0)

    def chat(self, *, messages: list[dict[str, Any]], temperature: float = 0.2) -> str:
        resp = self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        if resp.is_error:
            raise OllamaError(f"Ollama chat error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaError("Ollama chat returned unexpected format.")
        return content

