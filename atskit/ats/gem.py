"""Gem public boards API."""

from __future__ import annotations

import html

from .base import JobModel, html_to_markdown, polite_post

_GRAPHQL_URL = "https://jobs.gem.com/api/public/graphql/batch"


def list_jobs(slug: str) -> list[JobModel]:
    payload = [{
        "operationName": "JobBoardList",
        "variables": {"boardId": slug},
        "query": """query JobBoardList($boardId: String!) {
          oatsExternalJobPostings(boardId: $boardId) {
            jobPostings {
              id
              extId
              title
              locations { id name city isoCountry isRemote }
              job { id department { id name } locationType employmentType }
            }
          }
        }"""
    }]
    headers = {"Content-Type": "application/json", "batch": "true"}
    resp = polite_post(_GRAPHQL_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"[gem:{slug}] {resp.status_code} {resp.text[:200]}")
        return []

    data_list = resp.json()
    if not data_list or not data_list[0].get("data"):
        return []

    postings_data = data_list[0]["data"].get("oatsExternalJobPostings")
    if not postings_data:
        return []

    postings = postings_data.get("jobPostings", [])
    out: list[JobModel] = []

    for item in postings:
        locations = item.get("locations", [])
        loc_name = ""
        if locations:
            loc_name = locations[0].get("name", "")

        out.append(
            JobModel(
                id=str(item.get("extId", "")),
                title=item.get("title", ""),
                location=loc_name,
                description_md="",
                apply_url=f"https://jobs.gem.com/{slug}/{item.get('extId', '')}",
                raw=item,
            )
        )
    return out


def fetch_description(slug: str, job_id: str) -> str:
    payload = [{
        "operationName": "JobPosting",
        "variables": {"boardId": slug, "postingExtId": job_id},
        "query": "query JobPosting($boardId: String!, $postingExtId: String!) { oatsExternalJobPosting(boardId: $boardId, extId: $postingExtId) { id extId title descriptionHtml } }"
    }]
    headers = {"Content-Type": "application/json", "batch": "true"}
    resp = polite_post(_GRAPHQL_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        return ""

    data_list = resp.json()
    if not data_list or not data_list[0].get("data"):
        return ""

    posting = data_list[0]["data"].get("oatsExternalJobPosting")
    if not posting:
        return ""

    content = html.unescape(posting.get("descriptionHtml") or "")
    return html_to_markdown(content)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "retool"
    jobs = list_jobs(target)
    print(f"{target}: {len(jobs)} open roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
