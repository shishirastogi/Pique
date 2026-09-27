"""Google AI Studio Gemini provider (free tier). Keys: aistudio.google.com/apikey.

Resilience (docs trade-offs 2026 model churn + free-quota ceilings):
- 429: parses RetryInfo delay, retries ONCE (helps per-minute; daily quota
  still fails over to the next provider in the chain)
- 404 "model no longer available": auto-switches to the model the error
  suggests ("use models/...")
"""
import json
import logging
import re

import httpx

log = logging.getLogger("pique.ai.gemini")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_s: float = 15.0):
        self._key, self.model, self._timeout = api_key, model, timeout_s

    def complete(self, system: str, user: str, *, json_mode: bool = False,
                 timeout_s: float | None = None) -> str:
        return self._call_with_resilience(system, user, json_mode, timeout_s or self._timeout)

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> httpx.Response:
        gen_cfg: dict = {"temperature": 0.8}
        if json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        return httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self._key},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": gen_cfg,
            },
            timeout=timeout_s,
        )

    def _call_with_resilience(self, system, user, json_mode, timeout_s) -> str:
        r = self._call(system, user, json_mode, timeout_s)
        if r.status_code == 429:
            delay = _retry_delay(r)  # per-minute windows only
            if delay is not None and delay <= 25:
                import time
                time.sleep(delay + 0.5)
                r = self._call(system, user, json_mode, timeout_s)
        if r.status_code == 404:
            suggestion = _suggested_model(r)
            if suggestion and suggestion != self.model:
                log.info("gemini model %r retired; switching to %r", self.model, suggestion)
                self.model = suggestion
                r = self._call(system, user, json_mode, timeout_s)
        r.raise_for_status()
        data = r.json()
        return "".join(p.get("text", "") for p in
                       (data["candidates"][0]["content"]["parts"]))


def _retry_delay(r: httpx.Response) -> float | None:
    try:
        for d in r.json()["error"].get("details", []):
            if d.get("@type", "").endswith("RetryInfo"):
                return float(d["retryDelay"].rstrip("s"))
    except Exception:
        return None
    return None


def _suggested_model(r: httpx.Response) -> str | None:
    try:
        msg = r.json()["error"].get("message", "")
        m = re.search(r"models/([a-z0-9.\-]+)", msg)
        return m.group(1) if m else None
    except Exception:
        return None
