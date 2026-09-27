"""Embedding service (docs/09 — vector relevance for the candidate pool).

Provider: Gemini embedContent (separate quota from chat; disabled while the
dev key's credits are spent; local ONNX/sentence-transformers is the fallback
roadmap item). Auto-discovers a live embedding model name.
Failures are silent-None: retrieval then uses lexical overlap (09 §3 hybrid).
"""
import logging
import re

import httpx

from app.core.config import settings

log = logging.getLogger("pique.embeddings")

_CANDIDATE_MODELS = ["gemini-embedding-001", "text-embedding-004", "gemini-embedding-2"]


def _embed_once(model: str, texts: list[str], task: str) -> list[list[float]] | None:
    reqs = [{"model": f"models/{model}", "content": {"parts": [{"text": t}]},
             "taskType": task} for t in texts]
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents",
        params={"key": settings.llm_api_key},
        json={"requests": reqs}, timeout=25)
    if r.status_code == 404:
        m = re.search(r"models/([a-z0-9.\-]+)", r.json()["error"].get("message", ""))
        raise LookupError(m.group(1) if m else "")  # carry suggestion up
    r.raise_for_status()
    return [e["values"] for e in r.json()["embeddings"]]


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]] | None:
    """-> vectors or None (provider disabled/quota-spent). Enables cosine ranking."""
    if not settings.embeddings_enabled or not (settings.llm_api_key):
        return None
    try:
        return _embed_once(settings.embedding_model, texts, task)
    except LookupError as e:  # 404 with suggested model name
        if not e.args[0]:
            return None
        log.info("embedding model retired; following suggestion to %s", e.args[0])
        try:
            return _embed_once(e.args[0], texts, task)
        except Exception:
            return None
    except Exception as e_:
        log.warning("embedding failed (quota/offline?) – lexical path stays: %s", str(e_)[:120])
        return None
