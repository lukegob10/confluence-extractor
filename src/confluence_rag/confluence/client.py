from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urljoin

import httpx

from confluence_rag.confluence.models import ConfluencePage


class ConfluenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConfluenceAuth:
    mode: str  # bearer | basic
    token: str
    username: str | None = None

    def headers(self) -> dict[str, str]:
        if self.mode == "bearer":
            return {"Authorization": f"Bearer {self.token}"}
        if self.mode == "basic":
            if not self.username:
                raise ValueError("Basic auth requires username/email.")
            raw = f"{self.username}:{self.token}".encode("utf-8")
            return {"Authorization": f"Basic {base64.b64encode(raw).decode('utf-8')}"}
        raise ValueError(f"Unsupported auth mode: {self.mode}")


def _api_base_url(site_base_url: str) -> str:
    # Confluence Cloud typically uses https://<domain>.atlassian.net/wiki
    # Server/DC often uses https://confluence.company.com
    return urljoin(site_base_url.rstrip("/") + "/", "rest/api/")


class ConfluenceClient:
    def __init__(
        self,
        *,
        site_base_url: str,
        auth: ConfluenceAuth,
        verify_ssl: bool = True,
        timeout_s: float = 30.0,
    ) -> None:
        self._site_base_url = site_base_url.rstrip("/")
        self._api_base_url = _api_base_url(site_base_url)
        self._client = httpx.Client(
            base_url=self._api_base_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "confluence-rag/0.1.0",
                **auth.headers(),
            },
            verify=verify_ssl,
            timeout=timeout_s,
            follow_redirects=True,
        )

    @property
    def site_base_url(self) -> str:
        return self._site_base_url

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        max_attempts = 6
        backoff_s = 1.0
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.request(method, url, params=params)
                if response.status_code in {429, 500, 502, 503, 504}:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            sleep_s = max(0.0, float(retry_after))
                        except ValueError:
                            sleep_s = backoff_s
                    else:
                        sleep_s = backoff_s
                    if attempt < max_attempts:
                        time.sleep(sleep_s)
                        backoff_s = min(backoff_s * 2.0, 20.0)
                        continue
                if response.is_error:
                    raise ConfluenceError(
                        f"Confluence API error {response.status_code}: {response.text[:500]}"
                    )
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= max_attempts:
                    break
                time.sleep(backoff_s)
                backoff_s = min(backoff_s * 2.0, 20.0)

        raise ConfluenceError(f"Failed to call Confluence API after {max_attempts} attempts: {last_exc}")

    def list_spaces(self, *, limit: int = 200) -> Iterable[dict[str, Any]]:
        start = 0
        while True:
            resp = self._request("GET", "space", params={"start": start, "limit": limit})
            data = resp.json()
            results = data.get("results") or []
            for item in results:
                yield item
            if len(results) < limit:
                break
            start += len(results)

    def get_page(self, page_id: str) -> ConfluencePage:
        resp = self._request(
            "GET",
            f"content/{page_id}",
            params={"expand": "body.storage,version,space"},
        )
        return _page_from_content(resp.json(), site_base_url=self._site_base_url)

    def search_pages(
        self,
        *,
        cql: str,
        limit: int = 100,
    ) -> Iterable[ConfluencePage]:
        start = 0
        while True:
            resp = self._request(
                "GET",
                "content/search",
                params={
                    "cql": cql,
                    "start": start,
                    "limit": limit,
                    "expand": "body.storage,version,space",
                },
            )
            data = resp.json()
            results = data.get("results") or []
            for item in results:
                yield _page_from_content(item, site_base_url=self._site_base_url)
            if len(results) < limit:
                break
            start += len(results)


def _page_from_content(content: dict[str, Any], *, site_base_url: str) -> ConfluencePage:
    page_id = str(content.get("id") or "")
    title = str(content.get("title") or "")
    space = content.get("space") or {}
    space_key = space.get("key")

    version = content.get("version") or {}
    version_number = version.get("number")
    try:
        version_number_int = int(version_number) if version_number is not None else None
    except (TypeError, ValueError):
        version_number_int = None

    updated_at = version.get("when")

    links = content.get("_links") or {}
    webui = links.get("webui")
    base = links.get("base") or site_base_url
    url = urljoin(base.rstrip("/") + "/", webui.lstrip("/")) if webui else None

    body = content.get("body") or {}
    storage = body.get("storage") or {}
    body_storage = storage.get("value") or ""

    return ConfluencePage(
        id=page_id,
        title=title,
        space_key=space_key,
        url=url,
        version=version_number_int,
        updated_at=updated_at,
        body_storage=body_storage,
    )

