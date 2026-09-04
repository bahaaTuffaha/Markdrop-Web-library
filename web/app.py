"""FastAPI entry for the Markdrop web library."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import store
from .auth import COOKIE, PasswordMiddleware, cookie_value, is_authenticated, login
from .config import (
    MAX_UPLOAD_BYTES,
    PDF_MAGIC,
    apply_runtime_env,
    declared_extras,
    effective_engine,
    installed_extras,
    web_password,
)
from .jobs import JobManager
from .markdown_view import render_markdown
from .settings_store import public_settings, save_keys, save_settings, snapshot_for_job

logger = logging.getLogger("markdrop.web")
STATIC_DIR = Path(__file__).resolve().parent / "static"
jobs = JobManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    apply_runtime_env()
    jobs.start()
    yield
    jobs.stop()


app = FastAPI(title="Markdrop Library", lifespan=lifespan)
app.add_middleware(PasswordMiddleware)
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _spa() -> FileResponse:
    path = STATIC_DIR / "index.html"
    if not path.is_file():
        raise HTTPException(404, "Frontend is not built")
    return FileResponse(path)


def _book_or_404(book_id: str):
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return book


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    return {
        "ok": True,
        "engine": effective_engine(),
        "extras": installed_extras(),
        "declared_extras": declared_extras(),
        "auth_required": web_password() is not None,
        "authenticated": is_authenticated(request),
    }


@app.post("/api/login")
def api_login(payload: dict[str, Any]) -> JSONResponse:
    password = str(payload.get("password") or "")
    if not login(password):
        raise HTTPException(401, "Invalid password")
    response = JSONResponse({"ok": True})
    response.set_cookie(COOKIE, cookie_value(), httponly=True, samesite="lax", path="/")
    return response


@app.post("/api/logout")
def api_logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE, path="/")
    return response


@app.get("/api/library")
def api_library() -> dict[str, Any]:
    return {"books": [book.public_dict() for book in store.list_books()]}


@app.get("/api/library/stream")
async def api_library_stream():
    import asyncio
    import json

    async def events():
        last = ""
        while True:
            payload = json.dumps(
                {"books": [book.public_dict() for book in store.list_books()]},
                sort_keys=True,
            )
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload
            await asyncio.sleep(0.6)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/library")
async def api_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "document.pdf"
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is larger than 200 MB")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(400, "File is not a PDF")
    book = store.create_book(filename, data, snapshot_for_job())
    jobs.enqueue(book.id)
    return book.public_dict()


@app.get("/api/books/{book_id}")
def api_book(book_id: str) -> dict[str, Any]:
    return _book_or_404(book_id).public_dict()


@app.get("/api/books/{book_id}/markdown")
def api_markdown(book_id: str) -> Response:
    book = _book_or_404(book_id)
    path = store.find_markdown(book)
    if path is None:
        raise HTTPException(404, "Markdown is not ready yet")
    return Response(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@app.get("/api/books/{book_id}/rendered")
def api_rendered(book_id: str) -> Response:
    book = _book_or_404(book_id)
    path = store.find_markdown(book)
    if path is None:
        raise HTTPException(404, "Markdown is not ready yet")
    html = render_markdown(path.read_text(encoding="utf-8"), book_id)
    return Response(html, media_type="text/html; charset=utf-8")


@app.get("/api/books/{book_id}/files/{rel_path:path}")
def api_file(book_id: str, rel_path: str) -> FileResponse:
    _book_or_404(book_id)
    path = store.resolve_out_file(book_id, rel_path)
    if path is None:
        raise HTTPException(404, "File not found")
    return FileResponse(path)


@app.get("/api/books/{book_id}/cover")
def api_cover(book_id: str) -> FileResponse:
    _book_or_404(book_id)
    path = store.cover_path(book_id)
    if not path.is_file():
        raise HTTPException(404, "No cover")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/books/{book_id}/zip")
def api_zip(book_id: str) -> Response:
    book = _book_or_404(book_id)
    if book.status != "ready":
        raise HTTPException(409, "Book is not ready")
    blob = store.zip_out_bytes(book_id)
    filename = quote(f"{book.title}-markdroped.zip")
    return Response(
        blob,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.post("/api/books/{book_id}/cancel")
def api_cancel(book_id: str) -> dict[str, Any]:
    _book_or_404(book_id)
    book = jobs.cancel(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return book.public_dict()


@app.post("/api/books/{book_id}/retry")
def api_retry(book_id: str) -> dict[str, Any]:
    _book_or_404(book_id)
    book = jobs.retry(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return book.public_dict()


@app.delete("/api/books/{book_id}")
def api_delete(book_id: str) -> dict[str, Any]:
    _book_or_404(book_id)
    jobs.cancel(book_id)
    store.delete_book(book_id)
    return {"ok": True}


@app.get("/api/settings")
def api_get_settings() -> dict[str, Any]:
    return public_settings()


@app.put("/api/settings")
def api_put_settings(payload: dict[str, Any]) -> dict[str, Any]:
    body = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
    keys = payload.get("keys") if isinstance(payload.get("keys"), dict) else {}
    if body:
        save_settings(body)
    if keys:
        mapped: dict[str, str | None] = {}
        for key, value in keys.items():
            mapped[str(key)] = None if value is None else str(value)
        save_keys(mapped)
    return public_settings()


@app.get("/brand/logo.png")
def logo() -> FileResponse:
    path = Path(__file__).resolve().parent.parent / "markdrop" / "src" / "markdrop-logo.png"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return _spa()


@app.get("/login", response_class=HTMLResponse)
def login_page() -> FileResponse:
    return _spa()


@app.get("/settings", response_class=HTMLResponse)
def settings_page() -> FileResponse:
    return _spa()


@app.get("/books/{book_id}", response_class=HTMLResponse)
def reader_page(book_id: str) -> FileResponse:
    return _spa()
