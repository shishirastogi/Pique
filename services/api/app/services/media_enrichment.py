"""Media enrichment for GENERATED cards (docs/08 §1 optional providers).

Unlike ingestion providers (wikimedia/openverse/wikipedia — pool-building),
these run at generation time because their content is topical-by-construction:

- Imgflip: real meme TEMPLATES captioned in-house with our top/bottom text
  (owned captions; template shown per Imgflip API terms) → `meme` cards.
- GIPHY: real reaction GIFs hotlinked with "Powered by GIPHY" attribution →
  `reaction_gif` cards.

Both require free keys (docs/infra env.example). Without keys every call
returns None and cards fall back to the SVG renderer — never fatal.
"""
import logging
import time
import zlib

import httpx

from app.core.config import settings

log = logging.getLogger("pique.enrichment")

_TIMEOUT = 6.0
_meme_cache: dict = {"ts": 0.0, "templates": []}


def _enabled(provider: str) -> bool:
    return bool(settings.giphy_api_key) if provider == "giphy" else bool(
        settings.imgflip_username and settings.imgflip_password)


def caption_meme(top_text: str, bottom_text: str) -> dict | None:
    """-> {"url", "page_url"} or None. Requires PIQUE_IMGFLIP_USERNAME/PASSWORD."""
    if not _enabled("imgflip"):
        return None
    templates = _get_templates()
    if not templates:
        return None
    t = templates[zlib.crc32(top_text.encode()) % len(templates)]
    try:
        r = httpx.post("https://api.imgflip.com/caption_image", data={
            "template_id": t["id"],
            "username": settings.imgflip_username,
            "password": settings.imgflip_password,
            "text0": top_text[:80], "text1": bottom_text[:120],
        }, timeout=_TIMEOUT)
        data = r.json()
        if not data.get("success"):
            return None
        return {"url": data["data"]["url"], "page_url": data["data"]["page_url"],
                "template": t["name"]}
    except Exception as e:
        log.warning("imgflip caption failed: %s", e)
        return None


def _get_templates() -> list[dict]:
    if time.time() - _meme_cache["ts"] < 6 * 3600 and _meme_cache["templates"]:
        return _meme_cache["templates"]
    try:
        r = httpx.get("https://api.imgflip.com/get_memes", timeout=_TIMEOUT)
        memes = r.json().get("data", {}).get("memes", [])
        _meme_cache["templates"] = [m for m in memes if m.get("box_count", 2) == 2]
        _meme_cache["ts"] = time.time()
    except Exception as e:
        log.warning("imgflip template fetch failed: %s", e)
    return _meme_cache["templates"]


def find_gif(query: str) -> dict | None:
    """-> {"url", "page_url"} or None. Requires PIQUE_GIPHY_API_KEY."""
    if not _enabled("giphy"):
        return None
    try:
        r = httpx.get("https://api.giphy.com/v1/gifs/search", params={
            "api_key": settings.giphy_api_key, "q": query, "limit": 25,
            "rating": "pg-13", "lang": "en"}, timeout=_TIMEOUT)
        images = r.json().get("data", [])
        if not images:
            return None
        pick = images[zlib.crc32(query.encode()) % min(len(images), 10)]
        img = (pick.get("images") or {}).get("fixed_height") or {}
        return {"url": img.get("url"), "page_url": pick.get("url"),
                "title": pick.get("title")}
    except Exception as e:
        log.warning("giphy search failed: %s", e)
        return None
