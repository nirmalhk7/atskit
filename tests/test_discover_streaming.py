import time
import unittest
from pathlib import Path
from unittest.mock import patch

from atskit.discover import discover_jobs
from atskit.models import JobListing, PortalEntry, PortalJobsResult
from atskit.persistence import PortalStore


class TestDiscoverStreaming(unittest.TestCase):
    def test_yields_per_portal_as_results_complete(self):
        db_path = self._temp_db_path()
        store = PortalStore(db_path)
        store.replace(
            [
                PortalEntry(name="Fast", slug="fast", portal="lever", sample_url="https://example.com/fast"),
                PortalEntry(
                    name="Disabled",
                    slug="disabled",
                    portal="greenhouse",
                    sample_url="https://example.com/disabled",
                    status=False,
                ),
                PortalEntry(name="Slow", slug="slow", portal="greenhouse", sample_url="https://example.com/slow"),
            ]
        )
        store.close()

        queried: list[str] = []

        def fake_query(entry: PortalEntry):
            queried.append(entry.slug)
            if entry.slug == "slow":
                time.sleep(0.2)
            return [
                JobListing(
                    id=f"{entry.slug}-1",
                    title="Engineer",
                    location="Remote, US",
                    description_md="",
                    apply_url=f"https://example.com/{entry.slug}/1",
                )
            ], None

        with patch("atskit.discover._query_portal", side_effect=fake_query):
            results = list(
                discover_jobs(db_path, skip_scanned_today=False, max_workers=2, mark_scanned=False)
            )

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], PortalJobsResult)
        slugs = {result.entry.slug for result in results}
        self.assertEqual(slugs, {"fast", "slow"})
        self.assertCountEqual(queried, ["fast", "slow"])
        # Fast portal should finish before slow when using as_completed semantics.
        self.assertEqual(results[0].entry.slug, "fast")

    def _temp_db_path(self) -> Path:
        import tempfile

        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)
