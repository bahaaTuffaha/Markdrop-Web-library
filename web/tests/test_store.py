from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "MARKDROP_DATA_DIR",
    tempfile.mkdtemp(prefix="markdrop-web-test-", dir=tempfile.gettempdir()),
)

from web.settings_store import DEFAULT_SETTINGS, load_settings, save_keys, save_settings
from web.store import create_book, resolve_out_file, safe_filename, zip_out_bytes


class FilenameTests(unittest.TestCase):
    def test_strips_paths(self) -> None:
        self.assertEqual(safe_filename("../../etc/passwd.pdf"), "passwd.pdf")

    def test_adds_pdf_suffix(self) -> None:
        self.assertTrue(safe_filename("notes").endswith(".pdf"))


class SettingsTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        saved = save_settings({"convert_mode": "fast", "add_tables": True})
        loaded = load_settings()
        self.assertEqual(saved["add_tables"], True)
        self.assertEqual(loaded["add_tables"], True)
        self.assertIn("image_resolution_scale", DEFAULT_SETTINGS)

    def test_empty_key_keeps_existing(self) -> None:
        save_keys({"gemini": "abcd1234secret"})
        save_keys({"gemini": ""})
        from web.settings_store import load_keys

        self.assertEqual(load_keys()["gemini"], "abcd1234secret")


class LibraryTests(unittest.TestCase):
    def test_create_and_path_containment(self) -> None:
        try:
            import pymupdf
        except ImportError:
            self.skipTest("pymupdf is required")
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello")
        pdf_bytes = doc.tobytes()
        doc.close()

        book = create_book("My Paper.pdf", pdf_bytes, {"convert_mode": "fast"})
        self.assertEqual(book.status, "queued")
        self.assertTrue(book.source_name.endswith(".pdf"))

        out = Path(os.environ["MARKDROP_DATA_DIR"]) / "library" / book.id / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "ok.txt").write_text("hi", encoding="utf-8")
        self.assertIsNotNone(resolve_out_file(book.id, "ok.txt"))
        self.assertIsNone(resolve_out_file(book.id, "../book.json"))
        self.assertIsNone(resolve_out_file(book.id, "../../settings.json"))
        blob = zip_out_bytes(book.id)
        self.assertGreater(len(blob), 0)


if __name__ == "__main__":
    unittest.main()
