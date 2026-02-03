from __future__ import annotations

import httpx


class OpenAIError(RuntimeError):
    pass


class OpenAIEmbeddings:
    def __init__(self, *, api_key: str, model: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.post(
            "/embeddings",
            json={"model": self._model, "input": texts},
        )
        if resp.is_error:
            raise OpenAIError(f"OpenAI embeddings error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        items = data.get("data") or []
        embeddings: list[list[float]] = []
        for item in sorted(items, key=lambda x: x.get("index", 0)):
            embeddings.append(item.get("embedding"))
        if len(embeddings) != len(texts):
            raise OpenAIError("OpenAI embeddings returned unexpected number of vectors.")
        return embeddings

