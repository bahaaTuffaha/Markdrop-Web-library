"""Persistent conversion settings and API keys. Does not import `markdrop`."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import (
    declared_extras,
    effective_engine,
    installed_extras,
    markdrop_env_path,
    settings_path,
)

PROVIDER_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "litellm": "LITELLM_API_KEY",
}

CORE_PROVIDERS = {"gemini", "openai", "openrouter"}
EXTRA_PROVIDERS = {
    "anthropic": "anthropic",
    "groq": "groq",
    "litellm": "litellm",
}

DEFAULT_IMAGE_PROMPT = (
    "Provide a detailed, contextually rich description of this image. "
    "Include visual details, context, data, and any relevant information "
    "that would help someone understand what this image conveys without seeing it. "
    "Make it descriptive enough to serve as a replacement for the image."
)

DEFAULT_TABLE_PROMPT = (
    "Analyze this markdown table and provide a detailed description of its contents. "
    "Include key insights, patterns, and important details. Make the summary "
    "comprehensive enough to replace the original table.\n\nTable:\n"
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "convert_mode": "normal",
    "add_tables": False,
    "image_resolution_scale": 2.0,
    "download_button_color": "#444444",
    "enable_describe": False,
    "ai_provider": "gemini",
    "model": "",
    "text_model": "",
    "remove_images": False,
    "remove_tables": False,
    "image_descriptions": True,
    "table_descriptions": True,
    "max_retries": 3,
    "retry_delay": 2,
    "max_concurrency": 8,
    "timeout_seconds": 120,
    "image_prompt": DEFAULT_IMAGE_PROMPT,
    "table_prompt": DEFAULT_TABLE_PROMPT,
    "max_concurrent_jobs": 1,
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={values[key]}\n" for key in sorted(values)]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(lines), encoding="utf-8")
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:4] + "****"


def available_providers() -> list[str]:
    extras = set(installed_extras()) | set(declared_extras())
    providers = ["gemini", "openai", "openrouter"]
    for provider, extra in EXTRA_PROVIDERS.items():
        if extra in extras or extra in installed_extras():
            if provider not in providers:
                providers.append(provider)
    # Always list them; UI disables missing extras.
    for provider in EXTRA_PROVIDERS:
        if provider not in providers:
            providers.append(provider)
    return providers


def provider_status() -> dict[str, dict[str, bool]]:
    installed = set(installed_extras())
    status = {}
    for provider in ("gemini", "openai", "openrouter", "anthropic", "groq", "litellm"):
        extra = EXTRA_PROVIDERS.get(provider)
        if extra is None:
            status[provider] = {"available": True, "core": True}
        else:
            status[provider] = {"available": extra in installed, "core": False}
    return status


def load_settings() -> dict[str, Any]:
    merged = deepcopy(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in _read_json(settings_path()).items() if k in DEFAULT_SETTINGS})
    if effective_engine() == "lite":
        merged["convert_mode"] = "fast"
    return merged


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    for key, value in updates.items():
        if key not in DEFAULT_SETTINGS:
            continue
        expected = DEFAULT_SETTINGS[key]
        if isinstance(expected, bool):
            current[key] = bool(value)
        elif isinstance(expected, int) and not isinstance(expected, bool):
            current[key] = int(value)
        elif isinstance(expected, float):
            current[key] = float(value)
        elif isinstance(expected, str):
            current[key] = "" if value is None else str(value)
    if effective_engine() == "lite":
        current["convert_mode"] = "fast"
    current["convert_mode"] = "fast" if current["convert_mode"] == "fast" else "normal"
    if current["ai_provider"] not in PROVIDER_KEYS:
        current["ai_provider"] = "gemini"
    current["max_concurrent_jobs"] = max(1, min(4, int(current["max_concurrent_jobs"])))
    _write_json(settings_path(), current)
    return current


def load_keys() -> dict[str, str]:
    stored = _parse_env_file(markdrop_env_path())
    keys = {}
    for provider, env_name in PROVIDER_KEYS.items():
        keys[provider] = stored.get(env_name) or os.environ.get(env_name, "")
    return keys


def save_keys(updates: dict[str, str | None]) -> dict[str, str]:
    stored = _parse_env_file(markdrop_env_path())
    for provider, env_name in PROVIDER_KEYS.items():
        if provider not in updates:
            continue
        value = updates[provider]
        if value is None:
            stored.pop(env_name, None)
            os.environ.pop(env_name, None)
            continue
        text = str(value).strip()
        if not text or text.endswith("****"):
            continue
        stored[env_name] = text
        os.environ[env_name] = text
    _write_env_file(markdrop_env_path(), stored)
    for env_name, value in stored.items():
        os.environ[env_name] = value
    return load_keys()


def public_settings() -> dict[str, Any]:
    settings = load_settings()
    keys = load_keys()
    return {
        "settings": settings,
        "keys": {provider: mask_key(value) for provider, value in keys.items()},
        "engine": effective_engine(),
        "extras": installed_extras(),
        "providers": provider_status(),
    }


def snapshot_for_job() -> dict[str, Any]:
    snap = deepcopy(load_settings())
    snap["_engine"] = effective_engine()
    return snap
