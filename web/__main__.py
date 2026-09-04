from __future__ import annotations

import os

import uvicorn

from .config import apply_runtime_env


def main() -> None:
    apply_runtime_env()
    host = os.environ.get("MARKDROP_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("MARKDROP_WEB_PORT", "8080"))
    uvicorn.run("web.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
