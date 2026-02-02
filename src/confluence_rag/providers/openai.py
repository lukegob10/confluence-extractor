from __future__ import annotations

from typing import Any

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


class OpenAIChat:
    def __init__(self, *, api_key: str, model: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def chat(self, *, messages: list[dict[str, Any]], temperature: float = 0.2) -> str:
        resp = self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            },
        )
        if resp.is_error:
            raise OpenAIError(f"OpenAI chat error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise OpenAIError("OpenAI chat returned no choices.")
        msg = (choices[0].get("message") or {}).get("content")
        if not isinstance(msg, str):
            raise OpenAIError("OpenAI chat returned unexpected message format.")
        return msg

