from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault(
    "MARKDROP_DATA_DIR",
    tempfile.mkdtemp(prefix="markdrop-web-app-", dir=tempfile.gettempdir()),
)
os.environ.pop("MARKDROP_WEB_PASSWORD", None)

from fastapi.testclient import TestClient

from web.app import app


class AppTests(unittest.TestCase):
    def test_health_and_pages(self) -> None:
        with TestClient(app) as client:
            health = client.get("/api/health")
            self.assertEqual(health.status_code, 200)
            body = health.json()
            self.assertTrue(body["ok"])
            self.assertIn("engine", body)
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/settings").status_code, 200)
            self.assertEqual(client.get("/api/library").status_code, 200)

    def test_rejects_non_pdf(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/library",
                files={"file": ("notes.txt", b"not a pdf", "text/plain")},
            )
            self.assertEqual(response.status_code, 400)
