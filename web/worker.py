"""Subprocess worker. This is the only web module that imports `markdrop`."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

from .config import apply_runtime_env, data_dir, effective_engine
from .store import find_markdown, get_book, out_dir, source_pdf, update_book, write_progress

logger = logging.getLogger("markdrop.web.worker")


class _Ticker:
    def __init__(self, book_id: str, start: int, cap: int, seconds: float, stage: str) -> None:
        self.book_id = book_id
        self.start = start
        self.cap = cap
        self.seconds = max(seconds, 1.0)
        self.stage = stage
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start_thread(self) -> None:
        self._t0 = time.time()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            elapsed = time.time() - self._t0
            ratio = min(1.0, elapsed / self.seconds)
            percent = int(self.start + (self.cap - self.start) * ratio)
            write_progress(self.book_id, percent, self.stage, "Converting")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def _seconds_per_page(fast: bool) -> float:
    return 2.0 if fast else 10.0


def run_book(book_id: str) -> None:
    apply_runtime_env()
    book = get_book(book_id)
    if book is None:
        raise SystemExit(f"Unknown book {book_id}")

    from markdrop import (
        AIProvider,
        MarkDropConfig,
        ProcessorConfig,
        add_downloadable_tables,
        markdrop,
        process_markdown,
    )
    from markdrop.config_paths import load_markdrop_env

    load_markdrop_env()

    settings = book.settings or {}
    fast = settings.get("convert_mode") == "fast"
    if effective_engine() == "lite":
        fast = True
    if not fast and effective_engine() == "lite":
        raise RuntimeError("Normal convert needs MARKDROP_ENGINE=full (Docling).")

    pdf = source_pdf(book)
    if not pdf.is_file():
        raise FileNotFoundError(f"Missing source PDF: {pdf}")
    output = out_dir(book_id)
    output.mkdir(parents=True, exist_ok=True)

    pages = book.page_count or 8
    write_progress(book_id, 12, "convert", "Converting PDF")
    ticker = _Ticker(
        book_id,
        start=12,
        cap=79,
        seconds=pages * _seconds_per_page(fast),
        stage="convert",
    )
    ticker.start_thread()
    html_path: Path
    try:
        config = MarkDropConfig(
            fast=fast,
            image_resolution_scale=float(settings.get("image_resolution_scale", 2.0)),
            download_button_color=str(settings.get("download_button_color") or "#444444"),
        )
        html_path = markdrop(str(pdf), str(output), config)
    finally:
        ticker.stop()

    write_progress(book_id, 80, "convert", "Conversion finished")

    if settings.get("add_tables"):
        write_progress(book_id, 82, "tables", "Building Excel tables")
        add_downloadable_tables(html_path, config)

    md_path = html_path.with_suffix(".md")
    if settings.get("enable_describe"):
        write_progress(book_id, 90, "describe", "Generating AI descriptions")
        provider = str(settings.get("ai_provider") or "gemini")
        proc_kwargs: dict = {
            "input_path": str(md_path),
            "output_dir": str(output),
            "ai_provider": AIProvider(provider),
            "remove_images": bool(settings.get("remove_images")),
            "remove_tables": bool(settings.get("remove_tables")),
            "image_descriptions": bool(settings.get("image_descriptions", True)),
            "table_descriptions": bool(settings.get("table_descriptions", True)),
            "max_retries": int(settings.get("max_retries", 3)),
            "retry_delay": int(settings.get("retry_delay", 2)),
            "max_concurrency": int(settings.get("max_concurrency", 8)),
            "timeout_seconds": int(settings.get("timeout_seconds", 120)),
            "model_name_override": str(settings.get("model") or ""),
            "text_model_name_override": str(settings.get("text_model") or ""),
        }
        if settings.get("image_prompt"):
            proc_kwargs["image_prompt"] = str(settings["image_prompt"])
        if settings.get("table_prompt"):
            proc_kwargs["table_prompt"] = str(settings["table_prompt"])
        proc = ProcessorConfig(**proc_kwargs)
        md_path = asyncio.run(process_markdown(proc))

    latest = get_book(book_id) or book
    found = find_markdown(latest)
    markdown_file = found.name if found else Path(md_path).name
    update_book(
        book_id,
        status="ready",
        progress=100,
        stage="ready",
        message="Ready",
        error=None,
        markdown_file=markdown_file,
        pid=None,
    )
    write_progress(book_id, 100, "ready", "Ready")


def main() -> None:
    _configure_logging()
    parser = argparse.ArgumentParser(description="Markdrop library worker")
    parser.add_argument("--book-id", required=True)
    args = parser.parse_args()
    apply_runtime_env()
    logger.info("Worker start book=%s data=%s", args.book_id, data_dir())
    try:
        run_book(args.book_id)
    except Exception:
        logger.exception("Worker failed")
        try:
            update_book(
                args.book_id,
                status="failed",
                stage="failed",
                message="Conversion failed",
                error="Worker exception (see server logs)",
                pid=None,
            )
            write_progress(args.book_id, 0, "failed", "Conversion failed")
        except Exception:
            logger.exception("Could not record failure")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
