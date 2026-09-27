"""Wikimedia Commons provider (docs/08 §1). No key required.

Uses generator=search over File namespace with imageinfo+extmetadata, which
carries license/attribution fields we must preserve verbatim-ish.
"""
import logging

from app.providers.base import ProviderHttp, RawAsset, strip_html

log = logging.getLogger("pique.providers.wikimedia")

_NO_ATTR = {"cc0", "public domain", "cc 0", "public domain mark", "pdm"}
_DIAGRAM_HINTS = ("diagram", "chart", "map", "schematic", "flow", "graph", "cycle")


def _query_chain(query: str) -> list[str]:
    """Commons search ANDs terms: progressively drop trailing words until broad
    enough to return results (e.g. "quantum computing basics" -> "quantum computing")."""
    words = query.split()
    chain = [" ".join(words)]
    while len(words) > 2:
        words.pop()
        chain.append(" ".join(words))
    return chain


class WikimediaClient(ProviderHttp):
    name = "wikimedia"
    on_demand_ok = True

    def __init__(self, **http_kw):
        super().__init__("https://commons.wikimedia.org", **http_kw)

    def search(self, query: str, limit: int) -> list[RawAsset]:
        # Commons search ANDs words; long noisy queries -> retry with the core words
        for q in _query_chain(query):
            data = self.get_json("/w/api.php", params={
                "action": "query", "format": "json", "formatversion": "2",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {q}",
                "gsrnamespace": 6, "gsrlimit": min(max(limit, 1), 50),
                "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 800,
            })
            pages = (data.get("query") or {}).get("pages") or []
            if pages:
                break
        else:
            return []
        out: list[RawAsset] = []
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = _v(meta, "LicenseShortName")
            if not lic:
                continue  # no license info => unusable (provenance hard rule)
            title = (p.get("title") or "").removeprefix("File:")
            url = ii.get("thumburl") or ii.get("url")
            if not url:
                continue
            out.append(RawAsset(
                provider=self.name,
                source_id=str(p.get("pageid")),
                source_url=ii.get("descriptionurl") or "",
                media_url=url,
                title=strip_html(title),
                body=strip_html(_v(meta, "ImageDescription")) or "",
                creator=strip_html(_v(meta, "Artist")) or strip_html(_v(meta, "Credit")),
                license=lic,
                license_url=_v(meta, "LicenseUrl"),
                attribution_required=lic.lower() not in _NO_ATTR,
                attribution_text=_attribution(title, strip_html(_v(meta, "Artist")), lic),
                suggested_type=_suggest_type(title),
                meta={"width": ii.get("width"), "height": ii.get("height")},
            ))
        return out[:limit]


def _v(meta: dict, key: str) -> str | None:
    val = (meta.get(key) or {}).get("value")
    return val.strip() if isinstance(val, str) else None


def _attribution(title: str | None, artist: str | None, lic: str) -> str:
    t = title or "Untitled"
    by = f" by {artist}" if artist else ""
    return f"“{t}”{by}, {lic}, via Wikimedia Commons"


def _suggest_type(title: str) -> str:
    lower = title.lower()
    return "diagram" if any(h in lower for h in _DIAGRAM_HINTS) else "visual_explanation"
