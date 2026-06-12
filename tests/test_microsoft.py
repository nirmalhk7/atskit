import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

from atskit.ats import microsoft


class TestMicrosoftATS(unittest.TestCase):
    def _resp(self, payload, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = str(payload)
        resp.json.return_value = payload
        return resp

    def _position(self, job_id="1970393556635888", title="Software Engineer II"):
        return {
            "id": int(job_id),
            "displayJobId": "200011631",
            "name": title,
            "locations": ["United States, Washington, Redmond"],
            "standardizedLocations": ["Redmond, WA, US"],
            "postedTs": 1769645648,
            "department": "Software Engineering",
            "workLocationOption": "onsite",
            "locationFlexibility": None,
            "atsJobId": "200011631",
        }

    @patch("atskit.ats.microsoft._pause_between_pages")
    @patch("atskit.ats.microsoft.polite_get")
    def test_list_jobs_searches_us_software_engineer_filters(self, mock_get, mock_pause):
        mock_get.side_effect = [
            self._resp({"data": {"positions": [self._position("1970393556635888")], "count": 2}}),
            self._resp({"data": {"positions": [self._position("1970393556635889")], "count": 2}}),
        ]

        jobs = microsoft.list_jobs("microsoft")

        self.assertEqual(len(jobs), 2)
        self.assertEqual(mock_get.call_count, 2)
        mock_pause.assert_called_once()

        first_url = mock_get.call_args_list[0].args[0]
        second_url = mock_get.call_args_list[1].args[0]
        params = parse_qs(urlparse(first_url).query)
        self.assertEqual(params["domain"], ["microsoft.com"])
        self.assertEqual(params["query"], ["Software Engineer"])
        self.assertEqual(params["location"], ["United States"])
        self.assertEqual(params["start"], ["0"])
        self.assertEqual(params["filter_include_remote"], ["1"])
        self.assertEqual(params["filter_profession"], ["software engineering"])
        self.assertEqual(params["filter_seniority"], ["Entry", "Mid-Level"])
        self.assertEqual(parse_qs(urlparse(second_url).query)["start"], ["1"])

        headers = mock_get.call_args_list[0].kwargs["headers"]
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json, text/plain, */*")
        self.assertEqual(headers["Accept-Language"], "en-US,en;q=0.9")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Origin"], "https://apply.careers.microsoft.com")
        self.assertIn("apply.careers.microsoft.com/careers", headers["Referer"])
        self.assertEqual(headers["Sec-Fetch-Site"], "same-origin")
        self.assertEqual(headers["Sec-Fetch-Mode"], "cors")
        self.assertEqual(headers["Sec-Fetch-Dest"], "empty")
        self.assertEqual(headers["Connection"], "keep-alive")
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.microsoft._pause_between_pages")
    @patch("atskit.ats.microsoft.polite_get")
    def test_list_jobs_stops_on_empty_positions(self, mock_get, mock_pause):
        mock_get.side_effect = [
            self._resp({"data": {"positions": [self._position()], "count": 5}}),
            self._resp({"data": {"positions": [], "count": 5}}),
        ]

        jobs = microsoft.list_jobs("microsoft")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(mock_get.call_count, 2)
        mock_pause.assert_called_once()

    @patch("atskit.ats.microsoft._pause_between_pages")
    @patch("atskit.ats.microsoft.polite_get")
    def test_list_jobs_maps_metadata_and_raw_fields(self, mock_get, _mock_pause):
        mock_get.return_value = self._resp({
            "data": {
                "positions": [self._position()],
                "count": 1,
            }
        })

        jobs = microsoft.list_jobs("microsoft")

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, "1970393556635888")
        self.assertEqual(job.title, "Software Engineer II")
        self.assertEqual(job.location, "Redmond, WA, US")
        self.assertEqual(job.description_md, "")
        self.assertEqual(
            job.apply_url,
            "https://apply.careers.microsoft.com/careers/job/1970393556635888",
        )
        self.assertEqual(job.raw["displayJobId"], "200011631")
        self.assertEqual(job.raw["atsJobId"], "200011631")
        self.assertEqual(job.raw["postedTs"], 1769645648)
        self.assertEqual(job.raw["department"], "Software Engineering")
        self.assertEqual(job.raw["workLocationOption"], "onsite")
        self.assertIsNone(job.raw["locationFlexibility"])
        self.assertEqual(job.raw["country"], "US")

    @patch("atskit.ats.microsoft.polite_get")
    def test_list_jobs_failure_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "blocked"}, status_code=503)

        self.assertEqual(microsoft.list_jobs("microsoft"), [])

    @patch("atskit.ats.microsoft.polite_get")
    def test_fetch_description_converts_html_to_markdown(self, mock_get):
        mock_get.return_value = self._resp({
            "data": {
                "jobDescription": (
                    "<b>Overview</b><br><p>Build services.</p>"
                    "<b>Responsibilities</b><ul><li>Ship code</li></ul>"
                )
            }
        })

        text = microsoft.fetch_description("microsoft", "1970393556635888")

        self.assertIn("Overview", text)
        self.assertIn("Build services.", text)
        self.assertIn("Responsibilities", text)
        self.assertIn("Ship code", text)
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://apply.careers.microsoft.com/api/pcsx/position_details?position_id=1970393556635888&domain=microsoft.com&hl=en",
        )
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("/careers/job/1970393556635888", headers["Referer"])
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.microsoft.polite_get")
    def test_fetch_description_failure_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "not found"}, status_code=404)

        self.assertEqual(microsoft.fetch_description("microsoft", "1970393556635888"), "")


if __name__ == "__main__":
    unittest.main()
