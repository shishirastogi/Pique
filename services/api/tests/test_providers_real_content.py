"""Provider normalization + real-content session flow (docs/08, 11, 15 §2.4).

Offline: provider HTTP responses are fixtures; ingestion providers are stubs.
"""
import pytest

from app.core.config import settings
from app.db import SessionLocal, ContentSource, SessionItem, Content
from app.providers.base import RawAsset
from app.providers.openverse import OpenverseClient
from app.providers.wikimedia import WikimediaClient
from app.services import ingestion
from app.services.ingestion import _precheck

# ---------------- fixtures (real API response shapes, captured) ----------------

OPENVERSE_FIXTURE = {
    "result_count": 2,
    "results": [{
        "id": "abc-123", "title": "Carnot engine diagram", "creator": "Jane Doe",
        "license": "by-sa", "license_version": "4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "foreign_landing_url": "https://www.flickr.com/photos/x/1",
        "url": "https://live.staticflickr.com/x/1.jpg", "thumbnail": "https://t/x.jpg",
        "width": 1200, "height": 800,
        "attribution": "\"Carnot engine diagram\" by Jane Doe is licensed under CC BY-SA 4.0.",
    }, {
        "id": "def-456", "title": "Entropy sketch", "creator": None,
        "license": "cc0", "license_version": "1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "foreign_landing_url": "https://www.flickr.com/photos/x/2",
        "url": "https://live.staticflickr.com/x/2.jpg", "thumbnail": None,
        "width": None, "height": None,
        "attribution": "\"Entropy sketch\" is marked with CC0 1.0.",
    }],
}

WIKIMEDIA_FIXTURE = {
    "query": {"pages": [{
        "pageid": 991, "ns": 6, "title": "File:Stirling engine diagram.svg",
        "imageinfo": [{
            "url": "https://upload.wikimedia.org/x/full.png",
            "thumburl": "https://upload.wikimedia.org/x/800px.png",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Stirling_engine_diagram.svg",
            "width": 1600, "height": 1200,
            "extmetadata": {
                "LicenseShortName": {"value": "CC BY-SA 3.0"},
                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/3.0/"},
                "Artist": {"value": "<a href=\"https://x\">Some One</a>"},
                "ImageDescription": {"value": "<b>Schematic</b> of the engine."},
            },
        }],
    }, {
        "pageid": 992, "ns": 6, "title": "File:Old photo.jpg",
        "imageinfo": [{
            "url": "https://upload.wikimedia.org/y.jpg", "thumburl": None,
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Old_photo.jpg",
            "width": 800, "height": 600,
            "extmetadata": {"LicenseShortName": {"value": "Public domain"}},
        }],
    }, {
        "pageid": 993, "ns": 6, "title": "File:Unknown license.jpg",
        "imageinfo": [{"url": "https://upload.wikimedia.org/z.jpg",
                        "descriptionurl": "https://commons.wikimedia.org/z",
                        "width": 10, "height": 10, "extmetadata": {}}],
    }]},
}


class StubProvider:
    """Stand-in provider emitting CC-BY image assets (no network).
    Uses a whitelisted provider name because retrieval only pools genuinely
    sourced content (anti-recycling rule)."""
    name = "wikimedia"

    def search(self, query: str, limit: int):
        return [RawAsset(
            provider=self.name, source_id=f"{query}-{i}",
            source_url=f"https://src.example/{query}/{i}",
            media_url=f"https://cdn.example/{query}/{i}.jpg",
            title=f"{query} diagram {i}",
            license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution_required=True,
            attribution_text=f"“{query} diagram {i}” by Tester, CC BY 4.0",
            suggested_type="diagram",
        ) for i in range(limit)]


# ---------------- normalizer tests ----------------

def test_openverse_normalization(monkeypatch):
    client = OpenverseClient()
    monkeypatch.setattr(client, "get_json", lambda path, params: OPENVERSE_FIXTURE)
    assets = client.search("entropy", 5)
    assert len(assets) == 2

    by, cc0 = assets
    assert by.provider == "openverse" and by.source_id == "abc-123"
    assert by.license == "BY-SA 4.0" and by.attribution_required is True
    assert "CC BY-SA 4.0" in (by.attribution_text or "")
    assert by.suggested_type == "diagram"              # "diagram" hint in title
    assert cc0.attribution_required is False


def test_wikimedia_normalization(monkeypatch):
    client = WikimediaClient()
    monkeypatch.setattr(client, "get_json", lambda path, params: WIKIMEDIA_FIXTURE)
    assets = client.search("heat engine", 10)

    assert len(assets) == 2                             # page 993 dropped: no license
    diagram, pubdom = assets
    assert diagram.suggested_type == "diagram"
    assert diagram.media_url and diagram.media_url.endswith("800px.png")
    assert diagram.creator == "Some One"                # html stripped
    assert diagram.attribution_required is True
    assert "Wikimedia Commons" in (diagram.attribution_text or "")
    assert pubdom.attribution_required is False         # public domain


# ---------------- ingestion (S2/S3/S5-lite/S7-lite) ----------------

def test_ingestion_persists_provenance_and_dedups(monkeypatch):
    monkeypatch.setattr(ingestion, "enabled_providers", lambda: [StubProvider()])
    db = SessionLocal()

    report1 = ingestion.ingest_topic(db, "entropy waves", per_provider=4)
    # wikimedia-named stub also runs the diagram variant query: 4 + 2 assets
    assert report1["wikimedia"]["stored"] == 6

    report2 = ingestion.ingest_topic(db, "entropy waves", per_provider=4)
    assert report2["wikimedia"]["stored"] == 0
    assert report2["wikimedia"]["skipped_dup"] == 6    # idempotent rerun (11 §2)
    db.close()


def test_precheck_rules():
    assert _precheck(RawAsset(provider="p", source_id="1", source_url="u",
                              license=None)) == "license"          # hard rule (08 §3)
    assert _precheck(RawAsset(provider="p", source_id="1", source_url="u",
                              license="CC0", title="nsfw leak")) == "safety"
    assert _precheck(RawAsset(provider="p", source_id="1", source_url="u",
                              license="CC BY 4.0", media_url="http://insecure/x.jpg")) == "safety"


# ---------------- real-content session flow ----------------

def _task(client, auth, text="I need to study heat engines for my exam, I'm weak at it"):
    r = client.post("/api/v1/tasks/parse", headers=auth, json={"raw_text": text})
    return r.json()["task_id"]


def test_session_mixes_real_and_generated(client, auth, monkeypatch):
    # retrieval resolves enabled_providers via app.providers (on-demand path),
    # ingestion via its own import — patch both so the stub is used everywhere
    monkeypatch.setattr(ingestion, "enabled_providers", lambda: [StubProvider()])
    monkeypatch.setattr("app.providers.enabled_providers", lambda: [StubProvider()])
    monkeypatch.setattr(settings, "wikimedia_enabled", True)

    sid = client.post("/api/v1/sessions", headers=auth, json={
        "task_id": _task(client, auth), "duration_minutes": 10}).json()["session_id"]
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]

    # planner structure intact with a real pool (docs/10 invariants)
    assert len(items) == 20 and items[-1]["type"] == "first_work_action"
    types = [i["type"] for i in items]
    assert all(types[i] != types[i + 1] for i in range(len(types) - 1))

    # real provider cards landed in the sequence with media + attribution
    # (exclude rendered data-URI cards from the "provider-backed" set)
    real = [i for i in items if i["media"] and (i["media"].get("url") or "").startswith("http")]
    assert real, "expected real provider cards in the sequence"
    card = real[0]
    assert card["type"] == "diagram"
    assert card["media"]["url"].startswith("https://cdn.example/")
    assert card["attribution"]["required"] is True
    assert "CC BY 4.0" in card["attribution"]["text"]

    # INVARIANT (15 §2.4): every media card traces to provenance w/ license
    db = SessionLocal()
    try:
        rows = db.query(SessionItem, Content).join(
            Content, SessionItem.content_id == Content.id
        ).filter(SessionItem.session_id == sid).all()
        for _, content in rows:
            media = content.media or {}
            if media.get("url"):
                src = db.scalar(
                    __import__("sqlalchemy").select(ContentSource).where(
                        ContentSource.content_id == content.id))
                assert src is not None and src.license
    finally:
        db.close()

    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth,
                json={"started_work_confirmed": True})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})


def test_fallback_when_providers_disabled(client, auth):
    """Pool thin + all providers off -> all-generated session still works (04 §8)."""
    sid = client.post("/api/v1/sessions", headers=auth, json={
        "task_id": _task(client, auth, "I need to learn about Byzantine generals, I'm new to it"),
        "duration_minutes": 5}).json()["session_id"]
    items = client.get(f"/api/v1/sessions/{sid}/items", headers=auth).json()["items"]
    assert len(items) == 10 and items[-1]["type"] == "first_work_action"
    client.post(f"/api/v1/sessions/{sid}/complete", headers=auth, json={})
    client.post("/api/v1/lock/emergency-unlock", headers=auth, json={"confirm": "I NEED TO STOP"})
