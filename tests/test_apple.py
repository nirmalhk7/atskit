import unittest
from unittest.mock import MagicMock, patch

from atskit.ats import apple


class TestAppleATS(unittest.TestCase):
    def _resp(self, payload, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = str(payload)
        resp.json.return_value = payload
        return resp

    def _posting(self, apple_id="2001-1234", title="Software Engineer", location="Cupertino"):
        return {
            "id": apple_id,
            "positionId": apple_id.split("-")[0],
            "postingTitle": title,
            "transformedPostingTitle": "software-engineer",
            "postingDate": "Jun 05, 2026",
            "postDateInGMT": "2026-06-05T04:04:04.576Z",
            "team": {"teamName": "Software and Services"},
            "type": "REQ",
            "locations": [
                {
                    "name": location,
                    "countryID": "iso-country-USA",
                    "countryName": "United States of America",
                }
            ],
        }

    @patch("atskit.ats.apple._pause_between_pages")
    @patch("atskit.ats.apple.polite_post")
    def test_list_jobs_searches_newest_us_software_engineer_pages_1_to_5(self, mock_post, mock_pause):
        mock_post.side_effect = [
            self._resp({"res": {"searchResults": [self._posting(f"200{i}-1234")], "totalRecords": 5}})
            for i in range(1, 6)
        ]

        jobs = apple.list_jobs("apple")

        self.assertEqual(len(jobs), 5)
        self.assertEqual(mock_post.call_count, 5)
        self.assertEqual(mock_pause.call_count, 4)
        for page, call_args in enumerate(mock_post.call_args_list, 1):
            body = call_args.kwargs["json"]
            self.assertEqual(body["query"], "Software Engineer")
            self.assertEqual(body["filters"]["locations"], ["postLocation-USA"])
            self.assertEqual(body["locale"], "en-us")
            self.assertEqual(body["sort"], "newest")
            self.assertEqual(body["page"], page)
            self.assertEqual(body["format"]["mediumDate"], "MMM D, YYYY")
        headers = mock_post.call_args_list[0].kwargs["headers"]
        self.assertEqual(mock_post.call_args_list[1].kwargs["headers"], headers)
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json, text/plain, */*")
        self.assertEqual(headers["Accept-Language"], "en-US,en;q=0.9")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Origin"], "https://jobs.apple.com")
        self.assertIn("/en-us/search", headers["Referer"])
        self.assertEqual(headers["Sec-Fetch-Site"], "same-origin")
        self.assertEqual(headers["Sec-Fetch-Mode"], "cors")
        self.assertEqual(headers["Sec-Fetch-Dest"], "empty")
        self.assertEqual(headers["Connection"], "keep-alive")

    @patch("atskit.ats.apple._pause_between_pages")
    @patch("atskit.ats.apple.polite_post")
    def test_list_jobs_stops_on_empty_page(self, mock_post, mock_pause):
        mock_post.side_effect = [
            self._resp({"res": {"searchResults": [self._posting("2001-1234")]}}),
            self._resp({"res": {"searchResults": []}}),
        ]

        jobs = apple.list_jobs("apple")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(mock_post.call_count, 2)
        mock_pause.assert_called_once()

    @patch("atskit.ats.apple._pause_between_pages")
    @patch("atskit.ats.apple.polite_post")
    def test_list_jobs_skips_duplicate_apple_ids(self, mock_post, _mock_pause):
        mock_post.side_effect = [
            self._resp({
                "res": {
                    "searchResults": [
                        self._posting("2001-1234", location="Cupertino"),
                        self._posting("2001-1234", location="Austin"),
                    ]
                }
            }),
            self._resp({"res": {"searchResults": []}}),
        ]

        jobs = apple.list_jobs("apple")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Cupertino")

    @patch("atskit.ats.apple._pause_between_pages")
    @patch("atskit.ats.apple.polite_post")
    def test_list_jobs_maps_metadata_and_raw_fields(self, mock_post, _mock_pause):
        mock_post.side_effect = [
            self._resp({"res": {"searchResults": [self._posting()]}}),
            self._resp({"res": {"searchResults": []}}),
        ]

        jobs = apple.list_jobs("apple")

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, "2001-1234")
        self.assertEqual(job.title, "Software Engineer")
        self.assertEqual(job.location, "Cupertino")
        self.assertEqual(job.description_md, "")
        self.assertEqual(job.apply_url, "https://jobs.apple.com/en-us/details/2001-1234/software-engineer")
        self.assertEqual(job.raw["apple_id"], "2001-1234")
        self.assertEqual(job.raw["posting_date"], "Jun 05, 2026")
        self.assertEqual(job.raw["team"], {"teamName": "Software and Services"})
        self.assertEqual(job.raw["type"], "REQ")
        self.assertEqual(job.raw["locations"][0]["name"], "Cupertino")
        self.assertEqual(job.raw["country"], "US")

    @patch("atskit.ats.apple.polite_post")
    def test_list_jobs_failure_returns_safely(self, mock_post):
        mock_post.return_value = self._resp({"error": "blocked"}, status_code=503)

        self.assertEqual(apple.list_jobs("apple"), [])

    @patch("atskit.ats.apple.polite_get")
    def test_fetch_description_builds_markdown_from_detail_json(self, mock_get):
        mock_get.return_value = self._resp({
            "res": {
                "jobSummary": "Summary text.",
                "description": "Description text.",
                "minimumQualifications": "Min one\nMin two",
                "preferredQualifications": "Preferred one",
                "postingFooters": [
                    {
                        "localizations": {
                            "en_US": [
                                {
                                    "label": "Pay & Benefits",
                                    "type": "POSTING_FOOTER_RULES_NEW",
                                    "content": "<p>Base pay range.</p><ul><li>Medical</li></ul>",
                                },
                                {
                                    "type": "EEO_CONTENT_POSTING_FOOTER_RULES_NEW",
                                    "content": "<p>Legal footer.</p>",
                                },
                            ]
                        }
                    }
                ],
            }
        })

        text = apple.fetch_description("apple", "2001-1234")

        self.assertIn("## Summary", text)
        self.assertIn("Summary text.", text)
        self.assertIn("## Description", text)
        self.assertIn("Description text.", text)
        self.assertIn("## Minimum Qualifications", text)
        self.assertIn("Min one", text)
        self.assertIn("## Preferred Qualifications", text)
        self.assertIn("Preferred one", text)
        self.assertIn("## Pay & Benefits", text)
        self.assertIn("Base pay range.", text)
        self.assertIn("Medical", text)
        self.assertNotIn("Legal footer.", text)
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://jobs.apple.com/api/v1/jobDetails/2001-1234?locale=en-us",
        )
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("/en-us/details/2001-1234/", headers["Referer"])
        self.assertEqual(headers["Origin"], "https://jobs.apple.com")
        self.assertIn("Mozilla/5.0", headers["User-Agent"])

    @patch("atskit.ats.apple.polite_get")
    def test_fetch_description_failure_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "not found"}, status_code=404)

        self.assertEqual(apple.fetch_description("apple", "2001-1234"), "")


if __name__ == "__main__":
    unittest.main()
