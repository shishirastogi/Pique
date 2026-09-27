import os
import sys
import tempfile

import pytest

# isolate a throwaway sqlite DB BEFORE app import (settings read at import time)
_tmp = tempfile.mkdtemp(prefix="pique-test-")
os.environ["PIQUE_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
# tests must never hit external provider networks (docs/15 — hermetic CI)
os.environ["PIQUE_OPENVERSE_ENABLED"] = "false"
os.environ["PIQUE_WIKIMEDIA_ENABLED"] = "false"
os.environ["PIQUE_WIKIPEDIA_ENABLED"] = "false"
os.environ["PIQUE_GUTENBERG_ENABLED"] = "false"
# neutralize any real developer keys from infra/.env — env vars outrank dotenv
os.environ["PIQUE_LLM_PROVIDER"] = "none"
os.environ["PIQUE_LLM_API_KEY"] = ""
os.environ["PIQUE_GIPHY_API_KEY"] = ""
os.environ["PIQUE_IMGFLIP_USERNAME"] = ""
os.environ["PIQUE_IMGFLIP_PASSWORD"] = ""
os.environ["PIQUE_EMBEDDINGS_ENABLED"] = "false"
os.environ["PIQUE_LLM_PROVIDER"] = "none"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth(client) -> dict:
    r = client.post("/api/v1/auth/session", json={"device_fp": "test-device-0001"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
