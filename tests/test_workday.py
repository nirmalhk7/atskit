import unittest
from unittest.mock import MagicMock, patch

from atskit.ats import workday


class TestWorkdayATS(unittest.TestCase):
    def _resp(self, payload, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = str(payload)
        resp.json.return_value = payload
        return resp

    @patch("atskit.ats.workday._pause_between_pages")
    @patch("atskit.ats.workday._PAGE_SIZE", 2)
    @patch("atskit.ats.workday.polite_post")
    def test_list_jobs_paginates_full_board_without_search_text(self, mock_post, _mock_pause):
        slug = "example.wd1.myworkdayjobs.com|example|External"
        mock_post.side_effect = [
            self._resp({
                "total": 3,
                "jobPostings": [
                    {
                        "title": "Software Engineer",
                        "externalPath": "/job/San-Francisco-CA/Software-Engineer_R1",
                        "locationsText": "San Francisco, CA",
                        "bulletFields": ["R1"],
                    },
                    {
                        "title": "Member of Technical Staff",
                        "externalPath": "/job/New-York-NY/MTS_R2",
                        "locationsText": "New York, NY",
                        "bulletFields": ["R2"],
                    },
                ],
            }),
            self._resp({
                "total": 3,
                "jobPostings": [
                    {
                        "title": "Product Engineer",
                        "externalPath": "/job/Remote-US/Product-Engineer_R3",
                        "locationsText": "Remote US",
                        "bulletFields": ["R3"],
                    },
                ],
            }),
        ]

        jobs = workday.list_jobs(slug)

        self.assertEqual(len(jobs), 3)
        self.assertEqual(jobs[0].id, "R1")
        self.assertEqual(jobs[0].title, "Software Engineer")
        self.assertEqual(jobs[0].description_md, "")
        self.assertEqual(
            jobs[0].apply_url,
            "https://example.wd1.myworkdayjobs.com/en-US/External/job/San-Francisco-CA/Software-Engineer_R1",
        )
        self.assertEqual(jobs[0].raw["externalPath"], "/job/San-Francisco-CA/Software-Engineer_R1")
        self.assertEqual(mock_post.call_args_list[0].kwargs["json"]["searchText"], "")
        self.assertEqual(mock_post.call_args_list[0].kwargs["json"]["limit"], 2)
        headers = mock_post.call_args_list[0].kwargs["headers"]
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Origin"], "https://example.wd1.myworkdayjobs.com")
        self.assertEqual(headers["Referer"], "https://example.wd1.myworkdayjobs.com/en-US/External")
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(mock_post.call_args_list[1].kwargs["json"]["offset"], 2)
        self.assertEqual(mock_post.call_args_list[1].kwargs["headers"], headers)
        _mock_pause.assert_called_once()

    @patch("atskit.ats.workday.polite_get")
    def test_fetch_description_reads_detail_json_and_converts_html(self, mock_get):
        slug = "example.wd1.myworkdayjobs.com|example|External"
        mock_get.return_value = self._resp({
            "jobPostingInfo": {
                "title": "Software Engineer",
                "jobReqId": "R1",
                "jobDescription": "<h2>About the role</h2><p>Build APIs.</p><ul><li>Ship code</li></ul>",
            }
        })

        text = workday.fetch_description(slug, "/job/San-Francisco-CA/Software-Engineer_R1")

        self.assertIn("About the role", text)
        self.assertIn("Build APIs.", text)
        self.assertIn("Ship code", text)
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://example.wd1.myworkdayjobs.com/wday/cxs/example/External/job/San-Francisco-CA/Software-Engineer_R1",
        )
        headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(headers["Origin"], "https://example.wd1.myworkdayjobs.com")
        self.assertEqual(headers["Referer"], "https://example.wd1.myworkdayjobs.com/en-US/External")
        self.assertIn(headers["Accept"], {p["Accept"] for p in workday._HEADER_PROFILES})
        self.assertIn(headers["User-Agent"], {p["User-Agent"] for p in workday._HEADER_PROFILES})

    @patch("atskit.ats.workday._pause_between_pages")
    @patch("atskit.ats.workday._PAGE_SIZE", 2)
    @patch("atskit.ats.workday.polite_post")
    def test_list_jobs_keeps_first_total_when_later_pages_report_zero(self, mock_post, _mock_pause):
        slug = "example.wd1.myworkdayjobs.com|example|External"
        mock_post.side_effect = [
            self._resp({
                "total": 5,
                "jobPostings": [
                    {"title": "Role 1", "externalPath": "/job/A/Role-1_R1"},
                    {"title": "Role 2", "externalPath": "/job/A/Role-2_R2"},
                ],
            }),
            self._resp({
                "total": 0,
                "jobPostings": [
                    {"title": "Role 3", "externalPath": "/job/A/Role-3_R3"},
                    {"title": "Role 4", "externalPath": "/job/A/Role-4_R4"},
                ],
            }),
            self._resp({
                "total": 0,
                "jobPostings": [
                    {"title": "Role 5", "externalPath": "/job/A/Role-5_R5"},
                ],
            }),
        ]

        jobs = workday.list_jobs(slug)

        self.assertEqual(len(jobs), 5)
        self.assertEqual(mock_post.call_args_list[2].kwargs["json"]["offset"], 4)
        self.assertEqual(_mock_pause.call_count, 2)

    @patch("atskit.ats.workday.random.uniform", return_value=2.5)
    @patch("atskit.ats.workday.time.sleep")
    def test_pause_between_pages_uses_jitter(self, mock_sleep, mock_uniform):
        workday._pause_between_pages()

        mock_uniform.assert_called_once_with(*workday._PAGE_PAUSE_RANGE_S)
        mock_sleep.assert_called_once_with(2.5)

    @patch("atskit.ats.workday.polite_get")
    def test_fetch_description_requires_external_path(self, mock_get):
        text = workday.fetch_description("example.wd1.myworkdayjobs.com|example|External", "R1")

        self.assertEqual(text, "")
        mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
