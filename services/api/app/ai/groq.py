"""Groq provider (free dev tier, OpenAI-compatible). Keys: console.groq.com.

Resilience mirrors gemini.py: one 429 retry (Retry-After header) and automatic
model rollover via /models when a model is decommissioned.
"""
import logging

import httpx

log = logging.getLogger("pique.ai.groq")


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, timeout_s: float = 15.0):
        self._key, self.model, self._timeout = api_key, model, timeout_s
        self._h = {"Authorization": f"Bearer {api_key}"}

    def complete(self, system: str, user: str, *, json_mode: bool = False,
                 timeout_s: float | None = None) -> str:
        r = self._call(system, user, json_mode, timeout_s or self._timeout)
        if r.status_code == 429:
            delay = r.headers.get("Retry-After")
            try:
                wait_s = float(delay) if delay else 2.0
            except (ValueError, TypeError):
                wait_s = 2.0
            if wait_s <= 25:
                import time
                time.sleep(wait_s + 0.5)
                r = self._call(system, user, json_mode, timeout_s or self._timeout)
        if r.status_code in (400, 404) and "model" in r.text.lower():
            new_model = self._discover_model()
            if new_model and new_model != self.model:
                log.info("groq model %r unavailable; switching to %r", self.model, new_model)
                self.model = new_model
                r = self._call(system, user, json_mode, timeout_s or self._timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _call(self, system, user, json_mode, timeout_s) -> httpx.Response:
        body: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.8,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return httpx.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=self._h, json=body, timeout=timeout_s)

    def _discover_model(self) -> str | None:
        try:
            data = httpx.get("https://api.groq.com/openai/v1/models",
                             headers=self._h, timeout=10).json()
            ids = [m["id"] for m in data.get("data", [])]
            for pref in ("qwen", "llama-3", "llama", "mixtral", "gemma"):
                hit = next((i for i in ids if pref in i.lower()), None)
                if hit:
                    return hit
            return ids[0] if ids else None
        except Exception:
            return None
