"""LLM provider abstraction (docs/02 AI layer; idea doc §21: never hard-wire
one vendor). Config: PIQUE_LLM_PROVIDER=gemini|groq|none (comma list = failover
chain, e.g. "groq,gemini") + PIQUE_LLM_API_KEY (+ _KEY per provider), model
aliases auto-resolve to live versions.

Free tiers both work well for FocusWarmup's short-form generation:
- gemini: Google AI Studio key → gemini-flash-latest (free daily quota is small)
- groq:   console.groq.com key → Llama open models (larger free dev quota)
Anything else can implement ChatProvider and register below.
"""
import logging
from typing import Protocol

from app.core.config import settings

log = logging.getLogger("pique.ai")


class ChatProvider(Protocol):
    name: str
    def complete(self, system: str, user: str, *, json_mode: bool = False,
                 timeout_s: float | None = None) -> str: ...


_DEFAULT_MODEL = {"gemini": "gemini-flash-latest", "groq": "qwen/qwen3.8-27b"}
# last provider that answered successfully (for generated_by provenance/debug)
last_used: str | None = None


def _provider_keys() -> dict[str, str]:
    """PIQUE_LLM_API_KEY plus optional per-provider PIQUE_GEMINI_API_KEY /
    PIQUE_GROQ_API_KEY overrides (so the chain can hold multiple keys)."""
    keys = {}
    if settings.gemini_api_key or settings.llm_api_key:
        keys["gemini"] = settings.gemini_api_key or settings.llm_api_key
    if settings.groq_api_key or settings.llm_api_key:
        keys["groq"] = settings.groq_api_key or settings.llm_api_key
    return keys


def get_provider(name: str | None = None) -> ChatProvider | None:
    """None when unconfigured/misconfigured — every caller keeps a fallback."""
    name = (name or settings.llm_provider or "none").split(",")[0].strip().lower()
    if name in ("none", "", None):
        return None
    keys = _provider_keys()
    if not keys.get(name):
        return None
    model = settings.llm_model or _DEFAULT_MODEL.get(name, "")
    try:
        if name == "gemini":
            from app.ai.gemini import GeminiProvider
            return GeminiProvider(keys[name], model, settings.llm_timeout_s)
        if name == "groq":
            from app.ai.groq import GroqProvider
            return GroqProvider(keys[name], model, settings.llm_timeout_s)
    except Exception as e:
        log.warning("llm provider %r unavailable: %s", name, e)
        return None
    log.warning("unknown llm provider %r — disabled", name)
    return None


def complete(system: str, user: str, *, json_mode: bool = False,
             timeout_s: float | None = None) -> str | None:
    """Chain-aware completion: tries each provider in PIQUE_LLM_PROVIDER order.
    Returns None when none work — callers must have a non-LLM fallback."""
    names = [n.strip().lower() for n in (settings.llm_provider or "none").split(",")]
    global last_used
    for name in names:
        p = get_provider(name)
        if p is None:
            continue
        try:
            out = p.complete(system, user, json_mode=json_mode, timeout_s=timeout_s)
            last_used = name
            return out
        except Exception as e:
            log.warning("llm %r failed (%s); trying next in chain", name, str(e)[:160])
    return None
