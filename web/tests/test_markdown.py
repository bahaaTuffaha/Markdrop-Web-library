from __future__ import annotations

import unittest

from web.markdown_view import render_markdown


class MarkdownTests(unittest.TestCase):
    def test_rewrites_relative_images(self) -> None:
        html = render_markdown("![fig](images/a.png)", "book-1")
        self.assertIn('/api/books/book-1/files/images/a.png', html)
        self.assertIn("<img", html)

    def test_keeps_headings_and_strips_script(self) -> None:
        html = render_markdown("# Hello\n\n<script>alert(1)</script>", "book-1")
        self.assertIn("<h1>", html)
        self.assertNotIn("<script>", html)
