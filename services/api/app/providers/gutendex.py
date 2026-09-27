"""Project Gutenberg via Gutendex (docs/08 §1). DISABLED by default —
gutendex.com is slow/unreachable in some networks; enable with
PIQUE_GUTENBERG_ENABLED=true. Prefetch-only (book text fetch is too slow for
on-demand session fill).
"""
import re

from app.providers.base import ProviderHttp, RawAsset

_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.S)


class GutendexClient(ProviderHttp):
    name = "gutenberg"
    on_demand_ok = False  # downloads book text: prefetch-only (08 §5)

    def __init__(self):
        super().__init__()  # absolute URLs (books' text URLs vary)

    def search(self, query: str, limit: int) -> list[RawAsset]:
        data = self.get_json("https://gutendex.com/books", params={"search": query})
        out = []
        for b in (data.get("results") or [])[:limit]:
            url = (b.get("formats") or {}).get("text/plain; charset=utf-8") \
                or (b.get("formats") or {}).get("text/plain")
            authors = ", ".join(a.get("name", "") for a in (b.get("authors") or [])) or None
            excerpt = ""
            if url:
                try:
                    raw = self.get_text_head(url, max_chars=8000)
                    excerpt = _clean_excerpt(raw)
                except Exception:
                    continue  # prefetch quality: skip books we can't read
            if not excerpt:
                continue
            title = (b.get("title") or "Untitled").split("\n")[0]
            out.append(RawAsset(
                provider=self.name,
                source_id=str(b.get("id")),
                source_url=f"https://www.gutenberg.org/ebooks/{b.get('id')}",
                media_url=None,
                title=f"{title}" + (f" — {authors}" if authors else ""),
                body=excerpt,
                creator=authors,
                license="Public domain",
                license_url="https://www.gutenberg.org/policy/license.html",
                attribution_required=False,
                attribution_text=f"{title} by {authors or 'unknown'} (Project Gutenberg, public domain)",
                suggested_type="book_excerpt",
            ))
        return out


def _clean_excerpt(raw: str, max_len: int = 700) -> str:
    raw = _START.sub("", raw, count=1)  # strip PG header
    text = re.sub(r"\s+", " ", raw).strip()
    return text[:max_len].rsplit(" ", 1)[0] + "…" if len(text) > max_len else text
