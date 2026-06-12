import unittest
from unittest.mock import MagicMock, patch

from atskit.ats import amazon


class TestAmazonATS(unittest.TestCase):
    def _resp(self, payload, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = str(payload)
        resp.json.return_value = payload
        return resp

    def _posting(self, job_id="3092179", title="Software Engineer"):
        return {
            "id_icims": job_id,
            "id": "uuid-1",
            "title": title,
            "job_path": f"/en/jobs/{job_id}/software-engineer",
            "url_next_step": f"https://account.amazon.jobs/jobs/{job_id}/apply",
            "location": "Seattle, WA, USA",
            "country_code": "USA",
            "description": "<p>Build services.</p>",
            "basic_qualifications": "<ul><li>2+ years coding</li></ul>",
            "preferred_qualifications": "Distributed systems experience.",
        }

    @patch("atskit.ats.amazon.polite_get")
    def test_list_jobs_fetches_one_us_software_engineer_page(self, mock_get):
        mock_get.return_value = self._resp({"hits": 1, "jobs": [self._posting()]})

        jobs = amazon.list_jobs("amazon")

        self.assertEqual(len(jobs), 1)
        url = mock_get.call_args.args[0]
        self.assertIn("https://amazon.jobs/en/search.json?", url)
        self.assertIn("base_query=Software+Engineer", url)
        self.assertIn("loc_query=United+States", url)
        self.assertIn("country=USA", url)
        self.assertIn("result_limit=100", url)
        self.assertIn("sort=recent", url)
        self.assertIn("offset=0", url)
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json, text/plain, */*")
        self.assertEqual(headers["Accept-Language"], "en-US,en;q=0.9")
        self.assertIn("amazon.jobs/en/search", headers["Referer"])
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.amazon.polite_get")
    def test_list_jobs_paginates_to_200_recent_results(self, mock_get):
        first_page = [self._posting(str(3092000 + i)) for i in range(100)]
        second_page = [self._posting(str(3092100 + i)) for i in range(100)]
        mock_get.side_effect = [
            self._resp({"hits": 250, "jobs": first_page}),
            self._resp({"hits": 250, "jobs": second_page}),
        ]

        jobs = amazon.list_jobs("amazon")

        self.assertEqual(len(jobs), 200)
        self.assertEqual(mock_get.call_count, 2)
        first_url = mock_get.call_args_list[0].args[0]
        second_url = mock_get.call_args_list[1].args[0]
        self.assertIn("sort=recent", first_url)
        self.assertIn("result_limit=100", first_url)
        self.assertIn("offset=0", first_url)
        self.assertIn("offset=100", second_url)

    @patch("atskit.ats.amazon.polite_get")
    def test_list_jobs_maps_payload_to_job_model(self, mock_get):
        mock_get.return_value = self._resp({"jobs": [self._posting()]})

        jobs = amazon.list_jobs("amazon")

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, "3092179")
        self.assertEqual(job.title, "Software Engineer")
        self.assertEqual(job.location, "Seattle, WA, USA")
        self.assertEqual(job.apply_url, "https://amazon.jobs/en/jobs/3092179/software-engineer")
        self.assertIn("## Description", job.description_md)
        self.assertIn("Build services.", job.description_md)
        self.assertIn("## Basic Qualifications", job.description_md)
        self.assertIn("2\\+ years coding", job.description_md)
        self.assertIn("## Preferred Qualifications", job.description_md)
        self.assertEqual(job.raw["country"], "USA")
        self.assertEqual(job.raw["url_next_step"], "https://account.amazon.jobs/jobs/3092179/apply")

    @patch("atskit.ats.amazon.polite_get")
    def test_list_jobs_falls_back_to_path_id(self, mock_get):
        posting = self._posting()
        posting.pop("id_icims")
        posting.pop("id")
        mock_get.return_value = self._resp({"jobs": [posting]})

        jobs = amazon.list_jobs("amazon")

        self.assertEqual(jobs[0].id, "3092179")

    @patch("atskit.ats.amazon.polite_get")
    def test_list_jobs_non_200_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "blocked"}, status_code=503)

        self.assertEqual(amazon.list_jobs("amazon"), [])

    @patch("atskit.ats.amazon.polite_get")
    def test_fetch_description_searches_by_id_and_chooses_exact_match(self, mock_get):
        other = self._posting("1111111", title="Other Software Engineer")
        target = self._posting("3092179")
        mock_get.return_value = self._resp({"jobs": [other, target]})

        text = amazon.fetch_description("amazon", "3092179")

        self.assertIn("Build services.", text)
        url = mock_get.call_args.args[0]
        self.assertIn("base_query=3092179", url)
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("base_query=3092179", headers["Referer"])
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.amazon.polite_get")
    def test_fetch_description_returns_empty_for_non_200_or_missing_match(self, mock_get):
        mock_get.return_value = self._resp({"jobs": [self._posting("1111111")]})
        self.assertEqual(amazon.fetch_description("amazon", "3092179"), "")

        mock_get.return_value = self._resp({"error": "not found"}, status_code=404)
        self.assertEqual(amazon.fetch_description("amazon", "3092179"), "")


if __name__ == "__main__":
    unittest.main()
