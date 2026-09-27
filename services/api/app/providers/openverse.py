"""Openverse provider (docs/08 §1). Anonymous access; register for higher
limits (config OPENVERSE_* keys can be added when needed)."""
import logging

from app.providers.base import ProviderHttp, RawAsset

log = logging.getLogger("pique.providers.openverse")

_NO_ATTR = {"cc0", "pdm", "public-domain-mark"}
_DIAGRAM_HINTS = ("diagram", "chart", "map", "schematic", "flow", "graph", "cycle")


class OpenverseClient(ProviderHttp):
    name = "openverse"
    on_demand_ok = True

    def __init__(self, **http_kw):
        super().__init__("https://api.openverse.org", **http_kw)

    def search(self, query: str, limit: int) -> list[RawAsset]:
        data = self.get_json("/v1/images/", params={
            "q": query, "page_size": min(max(limit, 1), 50),
            "filter_dead": "true", "mature": "false",
            "source": "flickr,wikimedia,metmuseum,nypl",  # stable, well-licensed sources
        })
        out = []
        for r in data.get("results") or []:
            lic = (r.get("license") or "").upper()
            version = r.get("license_version") or ""
            if not lic:
                continue
            media_url = r.get("url") or r.get("thumbnail")
            if not media_url:
                continue
            out.append(RawAsset(
                provider=self.name,
                source_id=r.get("id") or media_url,
                source_url=r.get("foreign_landing_url") or media_url,
                media_url=media_url,
                title=r.get("title"),
                body="",
                creator=r.get("creator"),
                license=f"{lic} {version}".strip(),
                license_url=r.get("license_url"),
                attribution_required=lic.lower() not in _NO_ATTR,
                attribution_text=r.get("attribution"),  # Openverse ships ready-made strings
                suggested_type=_suggest_type(r.get("title") or ""),
                meta={"width": r.get("width"), "height": r.get("height")},
            ))
        return out[:limit]


def _suggest_type(title: str) -> str:
    lower = title.lower()
    return "diagram" if any(h in lower for h in _DIAGRAM_HINTS) else "visual_explanation"
