"""In-process supervisor that runs conversions in subprocesses."""

from __future__ import annotations

import gc
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import data_dir
from .models import ACTIVE_STATUSES, Book
from .settings_store import load_settings
from .store import get_book, list_books, update_book, wipe_out, write_progress

logger = logging.getLogger("markdrop.web.jobs")


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: list[str] = []
        self._procs: dict[str, subprocess.Popen[bytes]] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self.reconcile()
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="markdrop-jobs", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def reconcile(self) -> None:
        live_pids = set(self._procs)
        for book in list_books():
            if book.status == "queued" and book.id not in self._queue:
                self.enqueue(book.id)
            elif book.status in {"processing", "cancelling"} and book.id not in live_pids:
                if book.pid and _pid_alive(book.pid):
                    continue
                update_book(
                    book.id,
                    status="failed",
                    stage="failed",
                    message="Interrupted",
                    error="Worker stopped because the server restarted.",
                    pid=None,
                )
                write_progress(book.id, book.progress, "failed", "Interrupted")

    def enqueue(self, book_id: str) -> None:
        with self._lock:
            if book_id in self._queue or book_id in self._procs:
                return
            book = get_book(book_id)
            if book is None:
                return
            if book.status not in {"queued", "cancelled", "failed"}:
                if book.status in ACTIVE_STATUSES:
                    return
            update_book(
                book_id,
                status="queued",
                error=None,
                message="Waiting for worker",
                stage="queued",
                progress=max(book.progress, 10),
                pid=None,
            )
            write_progress(book_id, max(book.progress, 10), "queued", "Waiting for worker")
            self._queue.append(book_id)

    def retry(self, book_id: str) -> Book | None:
        book = get_book(book_id)
        if book is None:
            return None
        if book.status in {"queued", "processing", "uploading", "cancelling"}:
            return book
        wipe_out(book_id)
        update_book(
            book_id,
            status="queued",
            progress=10,
            stage="queued",
            message="Retry queued",
            error=None,
            markdown_file=None,
            pid=None,
        )
        self.enqueue(book_id)
        return get_book(book_id)

    def cancel(self, book_id: str) -> Book | None:
        with self._lock:
            book = get_book(book_id)
            if book is None:
                return None
            if book.status in {"ready", "cancelled", "failed"}:
                return book
            if book_id in self._queue:
                self._queue.remove(book_id)
                update_book(
                    book_id,
                    status="cancelled",
                    stage="cancelled",
                    message="Cancelled",
                    pid=None,
                )
                write_progress(book_id, book.progress, "cancelled", "Cancelled")
                wipe_out(book_id)
                return get_book(book_id)
            proc = self._procs.get(book_id)
            update_book(book_id, status="cancelling", stage="cancelling", message="Cancelling")
            write_progress(book_id, book.progress, "cancelling", "Cancelling")
            if proc is not None:
                _kill_proc(proc)
        return get_book(book_id)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._reap()
                self._start_next()
            except Exception:
                logger.exception("Job loop error")
            time.sleep(0.4)

    def _max_jobs(self) -> int:
        try:
            return max(1, min(4, int(load_settings().get("max_concurrent_jobs", 1))))
        except (TypeError, ValueError):
            return 1

    def _start_next(self) -> None:
        with self._lock:
            while self._queue and len(self._procs) < self._max_jobs():
                book_id = self._queue.pop(0)
                book = get_book(book_id)
                if book is None or book.status == "cancelled":
                    continue
                proc = self._spawn(book_id)
                self._procs[book_id] = proc
                update_book(
                    book_id,
                    status="processing",
                    stage="convert",
                    message="Starting conversion",
                    pid=proc.pid,
                    error=None,
                )
                write_progress(book_id, max(book.progress, 12), "convert", "Starting conversion")

    def _spawn(self, book_id: str) -> subprocess.Popen[bytes]:
        env = os.environ.copy()
        env["MARKDROP_DATA_DIR"] = str(data_dir())
        env["XDG_CONFIG_HOME"] = str(data_dir() / "config")
        env["PYTHONUNBUFFERED"] = "1"
        cmd = [
            sys.executable,
            "-m",
            "web.worker",
            "--book-id",
            book_id,
        ]
        return subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).resolve().parent.parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def _reap(self) -> None:
        with self._lock:
            finished = [book_id for book_id, proc in self._procs.items() if proc.poll() is not None]
        for book_id in finished:
            with self._lock:
                proc = self._procs.pop(book_id, None)
            if proc is None:
                continue
            code = proc.returncode
            output = b""
            if proc.stdout is not None:
                try:
                    output = proc.stdout.read() or b""
                except OSError:
                    output = b""
            book = get_book(book_id)
            if book is None:
                continue
            if book.status == "cancelling" or code == -signal.SIGTERM:
                wipe_out(book_id)
                update_book(
                    book_id,
                    status="cancelled",
                    stage="cancelled",
                    message="Cancelled",
                    pid=None,
                )
                write_progress(book_id, book.progress, "cancelled", "Cancelled")
                continue
            if code == 0:
                latest = get_book(book_id)
                if latest and latest.status != "ready":
                    update_book(book_id, status="ready", progress=100, stage="ready", pid=None)
                    write_progress(book_id, 100, "ready", "Done")
                else:
                    update_book(book_id, pid=None)
                continue
            tail = output.decode("utf-8", errors="replace")[-2000:]
            error = tail.strip() or f"Worker exited with code {code}"
            update_book(
                book_id,
                status="failed",
                stage="failed",
                message="Conversion failed",
                error=error,
                pid=None,
            )
            write_progress(book_id, book.progress, "failed", "Conversion failed")
            logger.error("Worker for %s failed: %s", book_id, error)
        gc.collect()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _kill_proc(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.terminate()
        except OSError:
            return
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            proc.kill()
