from __future__ import annotations

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

