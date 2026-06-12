import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

from atskit.ats import american_express


class TestAmericanExpressATS(unittest.TestCase):
    def _resp(self, payload, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = str(payload)
        resp.json.return_value = payload
        return resp

    def _posting(self, job_id="26007839", title="Software Engineer I", location="Phoenix, AZ, United States"):
        return {
            "Id": job_id,
            "Title": title,
            "PostedDate": "2026-06-01",
            "PostingEndDate": None,
            "PrimaryLocationCountry": "US",
            "PrimaryLocation": location,
            "Category": "Technology",
            "JobFunction": "Engineering & Architecture",
            "WorkplaceType": "Hybrid",
            "WorkplaceTypeCode": "ORA_HYBRID",
            "secondaryLocations": [
                {"Name": "Sunrise, FL, United States", "CountryCode": "US"},
                {"Name": "Sunrise, FL, United States", "CountryCode": "US"},
            ],
        }

    def _search_payload(self, postings, total=None):
        return {
            "items": [
                {
                    "TotalJobsCount": len(postings) if total is None else total,
                    "requisitionList": postings,
                }
            ]
        }

    @patch("atskit.ats.american_express._pause_between_pages")
    @patch("atskit.ats.american_express.polite_get")
    def test_list_jobs_searches_us_technology_software_engineer_filters_and_paginates(self, mock_get, mock_pause):
        first_page = [self._posting(f"260000{i:02d}") for i in range(10)]
        second_page = [
            self._posting("26000001", title="Duplicate Software Engineer"),
            self._posting("26000011", title="Software Engineer II"),
        ]
        mock_get.side_effect = [
            self._resp(self._search_payload(first_page, total=12)),
            self._resp(self._search_payload(second_page, total=12)),
        ]

        jobs = american_express.list_jobs("american_express")

        self.assertEqual(len(jobs), 11)
        self.assertEqual(mock_get.call_count, 2)
        mock_pause.assert_called_once()

        first_url = mock_get.call_args_list[0].args[0]
        second_url = mock_get.call_args_list[1].args[0]
        params = parse_qs(urlparse(first_url).query)
        self.assertEqual(params["onlyData"], ["true"])
        self.assertEqual(params["expand"], ["requisitionList.secondaryLocations"])
        finder = params["finder"][0]
        self.assertIn("findReqs;", finder)
        self.assertIn("siteNumber=CX_1", finder)
        self.assertIn("keyword=Software Engineer", finder)
        self.assertIn("selectedLocationsFacet=300000000229164", finder)
        self.assertIn("selectedFlexFieldsFacets=AttributeChar6|Technology", finder)
        self.assertIn("selectedPostingDatesFacet=30", finder)
        self.assertIn("limit=10", finder)
        self.assertIn("offset=0", finder)
        self.assertIn("offset=10", parse_qs(urlparse(second_url).query)["finder"][0])

        headers = mock_get.call_args_list[0].kwargs["headers"]
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json, text/plain, */*")
        self.assertEqual(headers["Accept-Language"], "en-US,en;q=0.9")
        self.assertEqual(headers["Origin"], "https://careers.americanexpress.com")
        self.assertIn("careers.americanexpress.com/en/sites/CX_1/jobs", headers["Referer"])
        self.assertEqual(headers["Sec-Fetch-Site"], "cross-site")
        self.assertEqual(headers["Sec-Fetch-Mode"], "cors")
        self.assertEqual(headers["Sec-Fetch-Dest"], "empty")
        self.assertEqual(headers["Connection"], "keep-alive")
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.american_express.polite_get")
    def test_list_jobs_maps_metadata_and_raw_fields(self, mock_get):
        mock_get.return_value = self._resp(self._search_payload([self._posting()]))

        jobs = american_express.list_jobs("american_express")

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, "26007839")
        self.assertEqual(job.title, "Software Engineer I")
        self.assertEqual(job.location, "Phoenix, AZ, United States, Sunrise, FL, United States")
        self.assertEqual(job.description_md, "")
        self.assertEqual(
            job.apply_url,
            "https://careers.americanexpress.com/en/sites/CX_1/job/26007839",
        )
        self.assertEqual(job.raw["postedDate"], "2026-06-01")
        self.assertEqual(job.raw["primaryLocationCountry"], "US")
        self.assertEqual(job.raw["category"], "Technology")
        self.assertEqual(job.raw["jobFunction"], "Engineering & Architecture")
        self.assertEqual(job.raw["workplaceType"], "Hybrid")
        self.assertEqual(job.raw["workplaceTypeCode"], "ORA_HYBRID")
        self.assertEqual(job.raw["country"], "US")

    @patch("atskit.ats.american_express.polite_get")
    def test_list_jobs_failure_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "blocked"}, status_code=503)

        self.assertEqual(american_express.list_jobs("american_express"), [])

    @patch("atskit.ats.american_express.polite_get")
    def test_fetch_description_builds_markdown_from_detail_json(self, mock_get):
        mock_get.return_value = self._resp({
            "items": [
                {
                    "ExternalDescriptionStr": "<p>Build customer platforms.</p>",
                    "ExternalResponsibilitiesStr": "<ul><li>Ship services</li></ul>",
                    "ExternalQualificationsStr": "<p>1-3 years of experience</p>",
                    "CorporateDescriptionStr": "<p>At American Express, ideas matter.</p>",
                    "OrganizationDescriptionStr": "<p>Benefits include medical.</p>",
                    "requisitionFlexFields": [
                        {
                            "Prompt": "Salary Range",
                            "Value": "$78000 - $124750 annually + bonus + benefits",
                        },
                        {"Prompt": "Career Area", "Value": "Technology"},
                    ],
                }
            ]
        })

        text = american_express.fetch_description("american_express", "26007839")

        self.assertIn("## Description", text)
        self.assertIn("Build customer platforms.", text)
        self.assertIn("## Responsibilities", text)
        self.assertIn("Ship services", text)
        self.assertIn("## Qualifications", text)
        self.assertIn("1\\-3 years of experience", text)
        self.assertIn("## About American Express", text)
        self.assertIn("ideas matter", text)
        self.assertIn("## Benefits", text)
        self.assertIn("Benefits include medical.", text)
        self.assertIn("## Salary Range", text)
        self.assertIn("$78000 - $124750 annually + bonus + benefits", text)
        self.assertNotIn("Career Area", text)

        mock_get.assert_called_once()
        params = parse_qs(urlparse(mock_get.call_args.args[0]).query)
        self.assertEqual(params["expand"], ["all"])
        self.assertEqual(params["onlyData"], ["true"])
        self.assertEqual(params["finder"], ['ById;Id="26007839",siteNumber=CX_1'])
        headers = mock_get.call_args.kwargs["headers"]
        self.assertIn("/en/sites/CX_1/job/26007839", headers["Referer"])
        self.assertNotIn("Cookie", headers)

    @patch("atskit.ats.american_express.polite_get")
    def test_fetch_description_failure_returns_safely(self, mock_get):
        mock_get.return_value = self._resp({"error": "not found"}, status_code=404)

        self.assertEqual(american_express.fetch_description("american_express", "26007839"), "")


if __name__ == "__main__":
    unittest.main()
