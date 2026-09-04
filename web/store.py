"""Filesystem library. Each book is a folder; JSON is the index."""

from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from .config import library_dir
from .cover import render_cover
from .models import ACTIVE_STATUSES, Book, Progress, utc_now

_lock = threading.RLock()
_SAFE_NAME = re.compile(r"[^\w.\- ()[\]]+", re.UNICODE)


def safe_filename(name: str) -> str:
    base = Path(name).name.strip() or "document.pdf"
    base = _SAFE_NAME.sub("_", base)
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base[:180] or "document.pdf"


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, sort_keys=True)
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def book_dir(book_id: str) -> Path:
    return library_dir() / book_id


def book_json_path(book_id: str) -> Path:
    return book_dir(book_id) / "book.json"


def progress_path(book_id: str) -> Path:
    return book_dir(book_id) / "progress.json"


def source_dir(book_id: str) -> Path:
    return book_dir(book_id) / "source"


def out_dir(book_id: str) -> Path:
    return book_dir(book_id) / "out"


def cover_path(book_id: str) -> Path:
    return book_dir(book_id) / "cover.jpg"


def source_pdf(book: Book) -> Path:
    return source_dir(book.id) / book.source_name


def write_progress(book_id: str, percent: int, stage: str, message: str = "") -> None:
    percent = max(0, min(100, int(percent)))
    _atomic_write(
        progress_path(book_id),
        Progress(percent=percent, stage=stage, message=message).to_dict(),
    )
    with _lock:
        book = get_book(book_id)
        if book is None:
            return
        book.progress = percent
        book.stage = stage
        book.message = message
        book.updated_at = utc_now()
        _save_book(book)


def _save_book(book: Book) -> None:
    book.updated_at = utc_now() or book.updated_at
    _atomic_write(book_json_path(book.id), book.to_dict())


def save_book(book: Book) -> Book:
    with _lock:
        if not book.updated_at:
            book.updated_at = utc_now()
        if not book.created_at:
            book.created_at = book.updated_at
        _save_book(book)
        return book


def update_book(book_id: str, **changes: Any) -> Book | None:
    with _lock:
        book = get_book(book_id)
        if book is None:
            return None
        for key, value in changes.items():
            if hasattr(book, key):
                setattr(book, key, value)
        _save_book(book)
        return book


def get_book(book_id: str) -> Book | None:
    raw = _read_json(book_json_path(book_id))
    if not raw:
        return None
    book = Book.from_dict(raw)
    progress = Progress.from_dict(_read_json(progress_path(book_id)))
    if book.status in ACTIVE_STATUSES and progress.stage:
        book.progress = progress.percent
        book.stage = progress.stage
        book.message = progress.message
    book.has_cover = cover_path(book_id).is_file()
    return book


def list_books() -> list[Book]:
    books: list[Book] = []
    root = library_dir()
    for child in root.iterdir():
        if not child.is_dir():
            continue
        book = get_book(child.name)
        if book is not None:
            books.append(book)
    books.sort(key=lambda item: item.created_at, reverse=True)
    return books


def iter_active() -> Iterable[Book]:
    for book in list_books():
        if book.status in ACTIVE_STATUSES:
            yield book


def create_book(filename: str, pdf_bytes: bytes, settings: dict[str, Any]) -> Book:
    book_id = str(uuid.uuid4())
    name = safe_filename(filename)
    title = Path(name).stem
    now = utc_now()
    book = Book(
        id=book_id,
        title=title,
        source_name=name,
        status="uploading",
        progress=2,
        stage="save",
        message="Saving PDF",
        created_at=now,
        updated_at=now,
        settings=settings,
    )
    dest_dir = source_dir(book_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_dir(book_id).mkdir(parents=True, exist_ok=True)
    pdf_path = dest_dir / name
    pdf_path.write_bytes(pdf_bytes)
    save_book(book)
    write_progress(book_id, 6, "cover", "Rendering cover")
    try:
        pages = render_cover(pdf_path, cover_path(book_id))
        update_book(book_id, page_count=pages, has_cover=True)
    except Exception:
        update_book(book_id, has_cover=False)
    queued = update_book(
        book_id,
        status="queued",
        progress=10,
        stage="queued",
        message="Waiting for worker",
        error=None,
    )
    assert queued is not None
    write_progress(book_id, 10, "queued", "Waiting for worker")
    return queued


def delete_book(book_id: str) -> bool:
    path = book_dir(book_id)
    if not path.exists():
        return False
    shutil.rmtree(path)
    return True


def wipe_out(book_id: str) -> None:
    path = out_dir(book_id)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def resolve_out_file(book_id: str, relative: str) -> Path | None:
    root = out_dir(book_id).resolve()
    if not root.is_dir():
        return None
    candidate = (root / relative).resolve()
    if not candidate.is_file():
        return None
    if not candidate.is_relative_to(root):
        return None
    return candidate


def find_markdown(book: Book) -> Path | None:
    out = out_dir(book.id)
    if book.markdown_file:
        path = out / book.markdown_file
        if path.is_file():
            return path
    processed = sorted(out.glob("*-markdroped_processed.md"))
    if processed:
        return processed[0]
    originals = sorted(out.glob("*-markdroped.md"))
    if originals:
        return originals[0]
    fallback = sorted(out.glob("*.md"))
    return fallback[0] if fallback else None


def zip_out_bytes(book_id: str) -> bytes:
    root = out_dir(book_id)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
    return buffer.getvalue()
