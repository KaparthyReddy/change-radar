"""Optional extraction with a local Ollama model. Model output is untrusted until verified."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from http.client import HTTPException
from typing import Any
from urllib.parse import urlsplit

from change_radar.extract.pipeline import ExtractionError
from change_radar.extract.prompts import SYSTEM_PROMPT, build_user_prompt
from change_radar.models import NO_DEADLINE, Alert, Item

DEFAULT_BASE_URL = "http://localhost:11434"
MAX_ALERTS_PER_ITEM = 3
MAX_TEXT_CHARS = 12_000
DEFAULT_TIMEOUT = 120.0

PostJson = Callable[[str, dict[str, Any]], dict[str, Any]]

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to the local model server and return the decoded reply."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read())
    except (OSError, HTTPException, ValueError) as exc:
        raise ExtractionError(f"could not reach the local model at {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExtractionError("the local model returned an unexpected response")
    return data


def _require_local(base_url: str) -> str:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or parts.hostname not in _LOCAL_HOSTS:
        raise ValueError("the model server must run on this machine (localhost)")
    return base_url.rstrip("/")


def _clean(entry: dict[str, Any], name: str) -> str:
    value = entry.get(name)
    return " ".join(value.split()) if isinstance(value, str) else ""


def _to_alert(entry: object, item: Item) -> Alert | None:
    if not isinstance(entry, dict):
        return None
    what_changed = _clean(entry, "what_changed")
    quote = _clean(entry, "quote")
    if not what_changed or not quote:
        return None
    return Alert(
        item_key=item.key,
        what_changed=what_changed,
        who_it_affects=_clean(entry, "who_it_affects") or "Not stated",
        deadline=_clean(entry, "deadline") or NO_DEADLINE,
        what_to_check=_clean(entry, "what_to_check") or "Read the full notice at the source.",
        quote=quote,
        source_url=item.url,
    )


def parse_reply(reply: dict[str, Any], item: Item) -> list[Alert]:
    """Turn a model reply into candidate alerts. Raises ExtractionError on malformed output."""
    message = reply.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ExtractionError("model reply has no message content")
    try:
        data = json.loads(content)
    except ValueError as exc:
        raise ExtractionError("model output was not valid JSON") from exc
    entries = data.get("alerts") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ExtractionError('model output has no "alerts" list')
    alerts: list[Alert] = []
    for entry in entries[:MAX_ALERTS_PER_ITEM]:
        alert = _to_alert(entry, item)
        if alert is not None:
            alerts.append(alert)
    return alerts


class OllamaExtractor:
    """Extractor backed by a model served locally by Ollama. No API keys."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        post: PostJson | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("a model name is required")
        self._model = model.strip()
        self._url = _require_local(base_url) + "/api/chat"
        self._post: PostJson = post or _post_json

    def __call__(self, item: Item) -> list[Alert]:
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(item.title, item.text[:MAX_TEXT_CHARS]),
                },
            ],
        }
        return parse_reply(self._post(self._url, payload), item)
