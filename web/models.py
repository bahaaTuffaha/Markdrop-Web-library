"""JSON-serializable records for the library and settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any

STATUSES = (
    "uploading",
    "queued",
    "processing",
    "ready",
    "cancelling",
    "cancelled",
    "failed",
)

ACTIVE_STATUSES = {"uploading", "queued", "processing", "cancelling"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Progress:
    percent: int = 0
    stage: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Progress:
        if not data:
            return cls()
        return cls(
            percent=int(data.get("percent") or 0),
            stage=str(data.get("stage") or ""),
            message=str(data.get("message") or ""),
        )


@dataclass
class Book:
    id: str
    title: str
    source_name: str
    status: str = "queued"
    progress: int = 0
    stage: str = ""
    message: str = ""
    error: str | None = None
    page_count: int | None = None
    has_cover: bool = False
    created_at: str = ""
    updated_at: str = ""
    markdown_file: str | None = None
    pid: int | None = None
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["cover_url"] = f"/api/books/{self.id}/cover" if self.has_cover else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Book:
        allowed = {item.name for item in fields(cls)}
        payload = {key: value for key, value in data.items() if key in allowed}
        payload.setdefault("settings", {})
        return cls(**payload)
