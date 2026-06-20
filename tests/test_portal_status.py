import unittest
from pathlib import Path

from atskit import PortalEntry, PortalStore, build_portals, sync_portals_from_applied


class TestPortalStatusPreservation(unittest.TestCase):
    def test_build_portals_preserves_disabled_rows(self):
        db_path = self._temp_db_path()
        store = PortalStore(db_path)
        store.replace(
            [
                PortalEntry(
                    name="Acme",
                    slug="acme",
                    portal="lever",
                    sample_url="https://jobs.lever.co/acme/123",
                    status=False,
                )
            ]
        )
        store.close()

        def applied_jobs():
            return [
                {
                    "company_name": "Acme",
                    "job_link": "https://jobs.lever.co/acme/abc-123",
                }
            ]

        build_portals(db_path, applied_jobs=applied_jobs, force_refresh=True)

        reloaded = PortalStore(db_path)
        acme = next(entry for entry in reloaded.load() if entry.name == "Acme")
        self.assertFalse(acme.status)
        self.assertEqual(acme.portal, "lever")
        reloaded.close()

    def test_sync_portals_from_applied_preserves_disabled_rows(self):
        db_path = self._temp_db_path()
        store = PortalStore(db_path)
        store.replace(
            [
                PortalEntry(
                    name="Acme",
                    slug="acme",
                    portal="lever",
                    sample_url="https://jobs.lever.co/acme/123",
                    status=False,
                )
            ]
        )
        store.close()

        def applied_jobs():
            return [
                {
                    "company_name": "Acme",
                    "job_link": "https://boards.greenhouse.io/acme/jobs/123456",
                }
            ]

        added = sync_portals_from_applied(db_path, applied_jobs)
        self.assertEqual(added, 1)

        reloaded = PortalStore(db_path)
        acme = next(entry for entry in reloaded.load() if entry.name == "Acme")
        self.assertFalse(acme.status)
        self.assertEqual(acme.portal, "greenhouse")
        reloaded.close()

    def _temp_db_path(self) -> Path:
        import tempfile

        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)
