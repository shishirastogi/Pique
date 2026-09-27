"""Card renderer (docs/11 §5 lite): turns text cards into visual SVG images so
memes/jokes/quotes/gifs are ALWAYS visual, even with zero external keys.
Returns a hotlink-free data URI — the renderer owns the asset (provider='mock',
license 'owned'). Zero dependencies; deterministic templates per type."""
import html
import textwrap
from urllib.parse import quote

RENDERED_TYPES = {"meme", "joke", "quote", "reaction_gif"}

_THEMES = {
    "meme":          {"bg0": "#2d1b4e", "bg1": "#1a1030", "accent": "#c084fc", "badge": "MEME"},
    "joke":          {"bg0": "#3d2c04", "bg1": "#1f1602", "accent": "#fbbf24", "badge": "JOKE"},
    "quote":         {"bg0": "#0d2b26", "bg1": "#071a17", "accent": "#5eead4", "badge": ""},
    "reaction_gif":  {"bg0": "#331427", "bg1": "#1c0b15", "accent": "#f472b6", "badge": "MOOD"},
}


def render_card(ctype: str, title: str | None, body: str) -> dict:
    """-> media dict {kind: 'image', url: data:image/svg+xml,...}."""
    theme = _THEMES.get(ctype, _THEMES["meme"])
    badge = theme["badge"]
    main = html.escape((body or title or "")[:220])
    lines = textwrap.wrap(main, 26) or [""]
    tspans = "".join(
        f'<tspan x="400" dy="{0 if i == 0 else 46}">{line}</tspan>'
        for i, line in enumerate(lines[:6])
    )
    y0 = 250 - (len(lines[:6]) - 1) * 23
    title_txt = html.escape((title or "")[:60])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{theme['bg0']}"/><stop offset="1" stop-color="{theme['bg1']}"/>
  </linearGradient></defs>
  <rect width="800" height="500" rx="18" fill="url(#g)"/>
  <circle cx="720" cy="60" r="90" fill="{theme['accent']}" opacity="0.12"/>
  <circle cx="60" cy="440" r="120" fill="{theme['accent']}" opacity="0.08"/>
  {f'<text x="40" y="56" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="{theme["accent"]}" letter-spacing="3">{badge}</text>' if badge else ''}
  {f'<text x="40" y="110" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="#e6edf3">{title_txt}</text>' if title_txt else ''}
  <text x="400" y="{y0}" text-anchor="middle" font-family="Arial, sans-serif" font-size="34"
        font-weight="bold" fill="#ffffff">{tspans}</text>
</svg>"""
    return {"kind": "image", "url": f"data:image/svg+xml;utf8,{quote(svg)}",
            "rendered": True, "width": 800, "height": 500}


def ensure_visual(payload: dict) -> dict:
    """Generated humor-type cards get a rendered SVG unless they already have
    real media (imgflip meme / giphy gif)."""
    if payload.get("type") in RENDERED_TYPES:
        media = payload.get("media") or {}
        if media.get("kind") == "none" or not media.get("url"):
            payload["media"] = render_card(payload["type"], payload.get("title"),
                                           payload.get("body", ""))
    return payload
