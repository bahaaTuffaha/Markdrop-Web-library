"""First-page PDF cover. Uses PyMuPDF directly — not the Markdrop package."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


def render_cover(pdf_path: Path, dest: Path, max_width: int = 480) -> int:
    """Render page 1 to JPEG. Returns page count."""
    doc = fitz.open(pdf_path)
    try:
        page_count = doc.page_count
        if page_count < 1:
            raise ValueError("PDF has no pages")
        page = doc[0]
        scale = max_width / max(page.rect.width, 1)
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        dest.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(dest), output="jpeg", jpg_quality=85)
        return page_count
    finally:
        doc.close()
