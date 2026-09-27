"""Wikipedia REST summaries provider — free, no key (docs/08).

Turns a topic into REAL text cards (interesting_fact) via page summaries:
Wikipedia text is CC BY-SA 4.0, so attribution is required and generated.
"""
import logging

from app.providers.base import ProviderHttp, RawAsset

log = logging.getLogger("pique.providers.wikipedia")

_LICENSE = "CC BY-SA 4.0"
_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


class WikipediaClient(ProviderHttp):
    name = "wikipedia"
    on_demand_ok = False  # N summary round-trips per topic: prefetch-only (08 §5)

    def __init__(self, lang: str = "en"):
        super().__init__(f"https://{lang}.wikipedia.org")

    def search(self, query: str, limit: int) -> list[RawAsset]:
        titles = self._resolve_titles(query, limit)
        out = []
        for title in titles:
            asset = self._summary_asset(title)
            if asset:
                out.append(asset)
        return out[:limit]

    def _resolve_titles(self, query: str, limit: int) -> list[str]:
        # progressively shorten multiword queries until opensearch finds pages
        words = query.split()
        while words:
            data = self.get_json("/w/api.php", params={
                "action": "opensearch", "format": "json", "namespace": 0,
                "profile": "fuzzy", "search": " ".join(words), "limit": min(limit, 5)})
            titles = data[1] if isinstance(data, list) and len(data) > 1 else []
            if titles:
                return titles
            words.pop()
        return []

    def _summary_asset(self, title: str) -> RawAsset | None:
        try:
            d = self.get_json(f"/api/rest_v1/page/summary/{title}", params={})
        except Exception:
            return None
        extract = (d.get("extract") or "").strip()
        page = (((d.get("content_urls") or {}).get("desktop") or {}).get("page")) or ""
        if not extract or not page or d.get("type") != "standard":
            return None
        thumb = d.get("thumbnail") or {}
        return RawAsset(
            provider=self.name,
            source_id=f"summary:{d.get('title', title)}",
            source_url=page,
            media_url=thumb.get("source"),
            title=d.get("title") or title,
            body=extract[:900],
            creator="Wikipedia contributors",
            license=_LICENSE,
            license_url=_LICENSE_URL,
            attribution_required=True,
            attribution_text=f"From Wikipedia article “{d.get('title', title)}”, CC BY-SA 4.0",
            suggested_type="interesting_fact",
            meta={"wikipedia_description": d.get("description") or ""},
        )
