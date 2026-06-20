import sqlite3
import unittest
from pathlib import Path

from atskit.models import PortalEntry
from atskit.persistence import PortalStore
from atskit.url import classify_url, clean_url, GREENHOUSE, LEVER


class TestURLClassification(unittest.TestCase):
    def test_classify_greenhouse_job_url(self):
        result = classify_url("https://boards.greenhouse.io/stripe/jobs/123456")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.portal, GREENHOUSE)
        self.assertEqual(result.slug, "stripe")
        self.assertEqual(result.job_id, "123456")

    def test_classify_lever_job_url(self):
        result = classify_url("https://jobs.lever.co/netflix/abc-123")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.portal, LEVER)
        self.assertEqual(result.slug, "netflix")
        self.assertEqual(result.job_id, "abc-123")

    def test_clean_url_strips_query_by_default(self):
        cleaned = clean_url("https://jobs.lever.co/acme/1?foo=bar")
        self.assertEqual(cleaned, "https://jobs.lever.co/acme/1")

    def test_clean_url_preserves_query_for_allowlisted_host(self):
        cleaned = clean_url(
            "https://example.com/jobs/1?foo=bar",
            preserve_query_domains={"example.com"},
        )
        self.assertEqual(cleaned, "https://example.com/jobs/1?foo=bar")


class TestPortalStore(unittest.TestCase):
    def test_replace_and_load_round_trip(self):
        with self.subTest("temp db"):
            db_path = Path(self._get_temp_db())
            store = PortalStore(db_path)
            entries = [
                PortalEntry(
                    name="Stripe",
                    slug="stripe",
                    portal="greenhouse",
                    sample_url="https://boards.greenhouse.io/stripe",
                    status=False,
                )
            ]
            store.replace(entries)
            loaded = store.load()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].name, "Stripe")
            self.assertFalse(loaded[0].status)
            store.close()

    def test_migrates_legacy_tables_to_add_status(self):
        db_path = Path(self._get_temp_db())
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE portal_entries (
                name TEXT PRIMARY KEY,
                slug TEXT NOT NULL,
                portal TEXT NOT NULL,
                sample_url TEXT NOT NULL,
                updated_on TEXT NOT NULL,
                last_scanned_date TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            INSERT INTO portal_entries(name, slug, portal, sample_url, updated_on, last_scanned_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Stripe",
                "stripe",
                "greenhouse",
                "https://boards.greenhouse.io/stripe",
                "2026-06-01",
                "",
            ),
        )
        conn.commit()
        conn.close()

        store = PortalStore(db_path)
        loaded = store.load()
        self.assertEqual(len(loaded), 1)
        self.assertTrue(loaded[0].status)
        with sqlite3.connect(db_path) as check_conn:
            columns = {row[1] for row in check_conn.execute("PRAGMA table_info(portal_entries)")}
        self.assertIn("status", columns)
        store.close()

    def _get_temp_db(self) -> str:
        import tempfile

        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name
