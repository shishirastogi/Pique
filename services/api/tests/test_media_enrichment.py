"""Card renderer + media enrichment (offline) and humor-visual invariant."""
from app.services import card_renderer, media_enrichment


def test_renderer_produces_visual_svg_for_humor_types():
    for ctype in ("meme", "joke", "quote", "reaction_gif"):
        payload = {"type": ctype, "title": "Test <T> & t", "body": "some body <b>"}
        card_renderer.ensure_visual(payload)
        media = payload["media"]
        assert media["kind"] == "image"
        assert media["url"].startswith("data:image/svg+xml")
        # html-escaped inside svg (no raw <b> tag leak)
        assert "%3C" in media["url"]


def test_ensure_visual_skips_non_humor_and_keeps_real_media():
    p = {"type": "interesting_fact", "title": None, "body": "x",
         "media": {"kind": "none"}}
    card_renderer.ensure_visual(p)
    assert p["media"]["kind"] == "none"

    m = {"type": "meme", "title": "t", "body": "b",
         "media": {"kind": "image", "url": "https://real.example/m.jpg"}}
    card_renderer.ensure_visual(m)
    assert m["media"]["url"] == "https://real.example/m.jpg"   # untouched


def test_enrichment_disabled_without_keys(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.giphy_api_key", None)
    monkeypatch.setattr("app.core.config.settings.imgflip_username", None)
    monkeypatch.setattr("app.core.config.settings.imgflip_password", None)
    assert media_enrichment.caption_meme("top", "bottom") is None
    assert media_enrichment.find_gif("entropy study mood") is None


def test_generated_humor_cards_have_visual_media(client, auth):
    """Every meme/joke/reaction_gif card in a session must be visual (user rule)."""
    r = client.post("/api/v1/tasks/parse", headers=auth,
                    json={"raw_text": "I need to learn distributed systems, I'm new to it"})
    sid = client.post("/api/v1/sessions", headers=auth, json={
        "task_id": r.json()["task_id"], "duration_minutes": 10}).json()["session_id"]
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
    humor = [i for i in items if i["type"] in ("meme", "joke", "reaction_gif", "quote")]
    assert humor, "10-min session must contain humor cards"
    for c in humor:
        assert c["media"] and c["media"].get("url"), f"{c['type']} card had no visual"
    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})
