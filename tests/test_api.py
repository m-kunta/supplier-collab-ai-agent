"""FastAPI tests: health, briefing CRUD, and list pagination."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app, briefing_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_DIR = PROJECT_ROOT / "data" / "inbound" / "mock"

_POST_BODY = {
    "vendor": "Kelloggs",
    "meeting_date": "2026-04-03",
    "data_dir": "data/inbound/mock",
    "lookback_weeks": 13,
    "persona_emphasis": "both",
    "include_benchmarks": True,
    "output_format": "md",
    "category_filter": None,
}


class ApiHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_ok(self) -> None:
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})


class ApiBriefingsTests(unittest.TestCase):
    """POST /api/briefings runs the pipeline; LLM and file write are mocked."""

    _STUB_BRIEFING = "# Stub briefing\n\nOK.\n"

    def setUp(self) -> None:
        self.client = TestClient(app)
        briefing_store.clear()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _create_briefing(self) -> dict:
        """POST one Kelloggs briefing with mocked LLM and file write.

        Returns the parsed JSON response. The temp output directory is
        cleaned up automatically; use ``payload["output_files"]["md_path"]``
        to inspect the (now-deleted) path string if needed.
        """
        with tempfile.TemporaryDirectory() as tmp_output:
            with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
                with patch("src.agent.write_output") as mock_write:
                    mock_write.return_value = {
                        "md_path": Path(tmp_output) / "V1001_2026-04-03.md",
                    }
                    r = self.client.post("/api/briefings", json=_POST_BODY)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_create_briefing_returns_summary_json(self) -> None:
        payload = self._create_briefing()
        self.assertIn("id", payload)
        self.assertIn("created_at", payload)
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["vendor_id"], "V1001")
        self.assertEqual(payload["briefing_text"], self._STUB_BRIEFING)
        self.assertIsNotNone(payload.get("scorecard"))
        md_path = payload.get("output_files", {}).get("md_path", "")
        self.assertTrue(md_path.endswith("V1001_2026-04-03.md"))

    def test_create_briefing_unknown_vendor_returns_400(self) -> None:
        r = self.client.post(
            "/api/briefings",
            json={**_POST_BODY, "vendor": "UnknownCo"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("detail", r.json())

    def test_get_briefing_round_trip(self) -> None:
        payload = self._create_briefing()
        bid = payload["id"]
        fetched = self.client.get(f"/api/briefings/{bid}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["id"], bid)
        self.assertEqual(fetched.json()["briefing_text"], self._STUB_BRIEFING)

    def test_get_briefing_unknown_returns_404(self) -> None:
        r = self.client.get("/api/briefings/00000000-0000-0000-0000-000000000000")
        self.assertEqual(r.status_code, 404)

    def test_list_briefings_after_create(self) -> None:
        payload = self._create_briefing()
        lst = self.client.get("/api/briefings")
        self.assertEqual(lst.status_code, 200)
        body = lst.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["briefings"]), 1)
        self.assertEqual(body["briefings"][0]["vendor_id"], "V1001")
        self.assertEqual(body["briefings"][0]["status"], "complete")

    def test_list_briefings_limit(self) -> None:
        """?limit=N caps the returned rows while total reflects the full count."""
        for _ in range(3):
            self._create_briefing()
        lst = self.client.get("/api/briefings?limit=2")
        self.assertEqual(lst.status_code, 200)
        body = lst.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(len(body["briefings"]), 2)

    def test_llm_provider_override_is_passed(self) -> None:
        """llm_provider in the request body is reflected in llm_selection.provider."""
        with tempfile.TemporaryDirectory() as tmp_output:
            with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
                with patch("src.agent.write_output") as mock_write:
                    mock_write.return_value = {
                        "md_path": Path(tmp_output) / "V1001_2026-04-03.md",
                    }
                    r = self.client.post(
                        "/api/briefings",
                        json={**_POST_BODY, "llm_provider": "openai"},
                    )
        self.assertEqual(r.status_code, 200, r.text)
        payload = r.json()
        self.assertEqual(payload["llm_selection"]["provider"], "openai")


class ApiStreamDownloadVendorTests(unittest.TestCase):
    """Stream, download, and vendor-list endpoints."""

    _STUB_BRIEFING = "# Stub briefing\n\nOK.\n"

    def setUp(self) -> None:
        self.client = TestClient(app)
        briefing_store.clear()

    def _create_briefing(self) -> dict:
        with tempfile.TemporaryDirectory() as tmp_output:
            with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
                with patch("src.agent.write_output") as mock_write:
                    mock_write.return_value = {
                        "md_path": Path(tmp_output) / "V1001_2026-04-03.md",
                    }
                    r = self.client.post("/api/briefings", json=_POST_BODY)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # --- stream ---

    def test_stream_briefing_yields_sse(self) -> None:
        payload = self._create_briefing()
        bid = payload["id"]
        r = self.client.get(f"/api/briefings/{bid}/stream")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/event-stream", r.headers.get("content-type", ""))
        self.assertIn('"type": "token"', r.text)
        self.assertIn('"type": "done"', r.text)

    def test_stream_briefing_unknown_returns_404(self) -> None:
        r = self.client.get("/api/briefings/00000000-0000-0000-0000-000000000000/stream")
        self.assertEqual(r.status_code, 404)

    # --- download ---

    def test_download_briefing_file_missing_returns_410(self) -> None:
        """When the .md path recorded in the store no longer exists on disk → 410."""
        with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
            with patch("src.agent.write_output") as mock_write:
                # Return a path inside a directory that will be deleted immediately.
                with tempfile.TemporaryDirectory() as tmp_output:
                    mock_write.return_value = {
                        "md_path": Path(tmp_output) / "V1001_2026-04-03.md",
                    }
                    r = self.client.post("/api/briefings", json=_POST_BODY)
        # tmp_output is now deleted; file_path no longer exists.
        bid = r.json()["id"]
        dl = self.client.get(f"/api/briefings/{bid}/download")
        self.assertEqual(dl.status_code, 410)

    # --- vendors ---

    def test_list_vendors_returns_kelloggs(self) -> None:
        r = self.client.get("/api/vendors?data_dir=data/inbound/mock")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreater(body["total"], 0)
        vendor_ids = [v["vendor_id"] for v in body["vendors"]]
        self.assertIn("V1001", vendor_ids)

    def test_list_vendors_bad_dir_returns_404(self) -> None:
        r = self.client.get("/api/vendors?data_dir=nonexistent/path/xyz")
        self.assertEqual(r.status_code, 404)
