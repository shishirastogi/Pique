"""ProviderClient protocol + RawAsset (docs/08 §1).

Every provider implements search+normalize. Normalization PRODUCES provenance —
an asset without license metadata is unusable (docs/08 §3 hard rule).
"""
import re
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import settings

_HTML = re.compile(r"<[^>]+>")


def strip_html(s: str | None) -> str | None:
    if not s:
        return None
    return _HTML.sub("", s).strip() or None


@dataclass
class RawAsset:
    """Provider-agnostic asset between fetch and persist (docs/11 S1->S2)."""
    provider: str
    source_id: str
    source_url: str                 # landing page (attribution links here)
    media_url: str | None = None    # direct image/thumb URL (hotlink; bytes later)
    title: str | None = None
    body: str = ""                  # caption / excerpt / generated text
    creator: str | None = None
    license: str | None = None      # "CC BY-SA 4.0", "CC0", "Public domain", ...
    license_url: str | None = None
    attribution_required: bool = False
    attribution_text: str | None = None
    fetchable: bool = False         # may we store bytes? default no (license matrix §4)
    suggested_type: str = "visual_explanation"
    meta: dict = field(default_factory=dict)


class ProviderClient(Protocol):
    name: str
    on_demand_ok: bool  # fast enough for session-create fill? (docs/08 §5)

    def search(self, query: str, limit: int) -> list[RawAsset]: ...


class ProviderHttp:
    """Shared HTTP w/ timeouts + retries + polite UA (docs/08 §7). Sync — the
    slice's FastAPI handlers are sync defs, and on-demand fetch volume is tiny."""

    def __init__(self, base_url: str = "", *, connect: float | None = None,
                 read: float | None = None):
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(read or settings.provider_read_timeout,
                                  connect=connect or settings.provider_connect_timeout),
            headers={"User-Agent": settings.provider_user_agent},
            follow_redirects=True,
        )

    def get_json(self, path: str, params: dict) -> dict:
        last: Exception | None = None
        for attempt in range(3):  # retry x3 w/ backoff (08 §7)
            try:
                r = self._client.get(path, params=params)
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"http {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last = e
                if attempt < 2:
                    import time
                    time.sleep(0.5 * (attempt + 1))
        raise last  # type: ignore[misc]

    def get_text_head(self, url: str, max_chars: int = 6000) -> str:
        """First N chars of a plain-text resource (Gutenberg excerpts)."""
        with self._client.stream("GET", url) as r:
            r.raise_for_status()
            chunks, n = [], 0
            for chunk in r.iter_text():
                chunks.append(chunk)
                n += len(chunk)
                if n >= max_chars:
                    break
        return "".join(chunks)[:max_chars]


def tight(client: ProviderClient, *, connect: float = 2.0, read: float = 5.0) -> ProviderClient:
    """Shrink an HTTP provider's timeouts in place (on-demand path, docs/08 §5).
    Non-HTTP providers pass through unchanged."""
    if isinstance(client, ProviderHttp):
        client._client.timeout = httpx.Timeout(read, connect=connect)
    return client


def enabled_providers() -> list[ProviderClient]:
    """Provider registry — new sources plug in HERE (docs/08 §1).
    Next candidates (all free/keyed-free): NASA image library, Library of
    Congress, Smithsonian (api.data.gov key), Unsplash + GIPHY + Imgflip (keys),
    Open Trivia DB (no key), Open Library, Europeana (key)."""
    from app.providers.gutendex import GutendexClient
    from app.providers.openverse import OpenverseClient
    from app.providers.wikimedia import WikimediaClient
    from app.providers.wikipedia import WikipediaClient

    out: list[ProviderClient] = []
    if settings.wikipedia_enabled:
        out.append(WikipediaClient())
    if settings.wikimedia_enabled:
        out.append(WikimediaClient())
    if settings.openverse_enabled:
        out.append(OpenverseClient())
    if settings.gutenberg_enabled:
        out.append(GutendexClient())
    return out
