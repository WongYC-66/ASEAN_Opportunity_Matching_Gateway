"""LLM client that works with any OpenAI-compatible endpoint.

Configure with environment variables (or `backend/.env`):

    LLM_PRESET   openrouter | groq | gemini | openai | ollama | custom | none
    LLM_BASE_URL override / required for `custom`
    LLM_API_KEY  required for hosted providers
    LLM_MODEL    override the preset's default model
    LLM_TIMEOUT  request timeout in seconds (default 30)

Presets use free-tier friendly defaults. Without a key (and without a local
Ollama), matching falls back to the built-in heuristic engine.
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

PRESETS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "needs_key": True,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "needs_key": True,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "needs_key": True,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "needs_key": True,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "needs_key": False,
    },
    "custom": {
        "base_url": "",
        "model": "",
        "needs_key": False,
    },
    "none": {
        "base_url": "",
        "model": "",
        "needs_key": False,
    },
}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    preset: str
    base_url: str
    model: str
    api_key: Optional[str]
    needs_key: bool
    timeout: float

    @property
    def available(self) -> bool:
        if not self.base_url or not self.model:
            return False
        return bool(self.api_key) or not self.needs_key

    def status(self) -> Dict[str, Any]:
        return {
            "preset": self.preset,
            "base_url": self.base_url or None,
            "model": self.model or None,
            "api_key_set": bool(self.api_key),
            "available": self.available,
            "mode": "llm" if self.available else "heuristic",
            "presets": sorted(PRESETS),
        }


def get_config() -> LLMConfig:
    preset = (os.getenv("LLM_PRESET") or "openrouter").strip().lower()
    preset_cfg = PRESETS.get(preset, PRESETS["custom"])
    base_url = (os.getenv("LLM_BASE_URL") or preset_cfg["base_url"]).strip().rstrip("/")
    model = (os.getenv("LLM_MODEL") or preset_cfg["model"]).strip()
    api_key = (os.getenv("LLM_API_KEY") or "").strip() or None
    needs_key = bool(preset_cfg["needs_key"])
    try:
        timeout = float(os.getenv("LLM_TIMEOUT") or 30)
    except ValueError:
        timeout = 30.0
    return LLMConfig(
        preset=preset,
        base_url=base_url,
        model=model,
        api_key=api_key,
        needs_key=needs_key,
        timeout=timeout,
    )


def _extract_json(text: str) -> Any:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise LLMError("LLM response was not valid JSON")


def chat_json(
    system_prompt: str,
    user_prompt: str,
    config: Optional[LLMConfig] = None,
) -> Any:
    cfg = config or get_config()
    if not cfg.available:
        raise LLMError("LLM is not configured")

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    if cfg.preset == "openrouter":
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "Hack Teh Tarik Matcher"

    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }

    try:
        with httpx.Client(timeout=cfg.timeout) as client:
            response = client.post(
                f"{cfg.base_url}/chat/completions", headers=headers, json=payload
            )
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(
            f"LLM returned {response.status_code}: {response.text[:300]}"
        )

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError("Unexpected LLM response shape") from exc

    if not content or not content.strip():
        raise LLMError("LLM returned an empty response")
    return _extract_json(content)
