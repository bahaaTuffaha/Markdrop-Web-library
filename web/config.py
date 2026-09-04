"""Runtime paths and image capability flags. Does not import `markdrop`."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

EXTRA_MODULES = {
    "lite": "pymupdf4llm",
    "anthropic": "anthropic",
    "groq": "groq",
    "litellm": "litellm",
    "local-models": "ollama",
}

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
PDF_MAGIC = b"%PDF"


def data_dir() -> Path:
    raw = os.environ.get("MARKDROP_DATA_DIR", "").strip()
    path = Path(raw) if raw else Path.cwd() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def library_dir() -> Path:
    path = data_dir() / "library"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return data_dir() / "settings.json"


def config_home() -> Path:
    path = data_dir() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def markdrop_env_path() -> Path:
    env_dir = config_home() / "markdrop"
    env_dir.mkdir(parents=True, exist_ok=True)
    return env_dir / ".env"


def session_secret_path() -> Path:
    return data_dir() / ".session_secret"


def apply_runtime_env() -> None:
    """Point Markdrop's config_paths at the data volume without editing core."""
    os.environ.setdefault("XDG_CONFIG_HOME", str(config_home()))
    os.environ.setdefault("HF_HOME", str(data_dir() / "cache" / "hf"))


def declared_engine() -> str:
    value = os.environ.get("MARKDROP_ENGINE", "full").strip().lower()
    return "lite" if value == "lite" else "full"


def declared_extras() -> list[str]:
    raw = os.environ.get("MARKDROP_EXTRAS", "lite,litellm")
    extras = []
    for item in raw.split(","):
        name = item.strip()
        if name and name not in extras:
            extras.append(name)
    return extras


def installed_extras() -> list[str]:
    found = []
    for extra, module in EXTRA_MODULES.items():
        if importlib.util.find_spec(module) is not None:
            found.append(extra)
    return found


def docling_available() -> bool:
    return importlib.util.find_spec("docling") is not None


def effective_engine() -> str:
    if declared_engine() == "lite" or not docling_available():
        return "lite"
    return "full"


def web_password() -> str | None:
    value = os.environ.get("MARKDROP_WEB_PASSWORD", "").strip()
    return value or None
