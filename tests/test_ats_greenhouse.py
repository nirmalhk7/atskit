import unittest
from unittest.mock import MagicMock, patch

from atskit.ats import greenhouse


class TestGreenhouseClient(unittest.TestCase):
    @patch("atskit.ats.greenhouse.polite_get")
    def test_list_jobs_maps_response(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "jobs": [
                    {
                        "id": 1,
                        "title": "Software Engineer",
                        "location": {"name": "Remote"},
                        "content": "<p>Build things</p>",
                        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/1",
                    }
                ]
            },
        )

        jobs = greenhouse.list_jobs("stripe")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Software Engineer")
        self.assertIn("Build things", jobs[0].description_md)
