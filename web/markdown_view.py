"""Render book markdown to sanitized HTML. No browser JS vendors required."""

from __future__ import annotations

import re
from urllib.parse import quote

import bleach
import markdown

ALLOWED_TAGS = {
    "p",
    "pre",
    "code",
    "img",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "br",
    "blockquote",
    "ul",
    "ol",
    "li",
    "em",
    "strong",
    "a",
    "div",
    "span",
}

ALLOWED_ATTRS = {
    "img": ["src", "alt", "title"],
    "a": ["href", "title"],
    "code": ["class"],
    "pre": ["class"],
}


def _rewrite_src(src: str, book_id: str) -> str:
    if not src or src.startswith(("http://", "https://", "data:", "/")):
        return src
    cleaned = src.replace("\\", "/").lstrip("./")
    return "/api/books/" + book_id + "/files/" + quote(cleaned, safe="/")


def render_markdown(text: str, book_id: str) -> str:
    html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        output_format="html",
    )

    def repl(match: re.Match[str]) -> str:
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        return f"{prefix}{_rewrite_src(src, book_id)}{suffix}"

    html = re.sub(r'(src=")([^"]+)(")', repl, html)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=["http", "https"],
        strip=True,
    )
