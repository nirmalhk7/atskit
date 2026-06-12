"""Ashby job board API.

Ashby exposes a public GraphQL endpoint at
`https://jobs.ashbyhq.com/api/non-user-graphql`. The `ApiJobBoardWithTeams`
operation returns all open jobs for a hosted-jobs-page slug.
"""

from __future__ import annotations

import html

from .base import JobModel, html_to_markdown, polite_post


_GRAPHQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
_QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    teams { id name parentTeamId }
    jobPostings {
      id
      title
      teamId
      locationName
      employmentType
      secondaryLocations { locationName }
      address { locationName country }
      compensationTierSummary
    }
  }
}
""".strip()


def list_jobs(slug: str) -> list[JobModel]:
    body = {
        "operationName": "ApiJobBoardWithTeams",
        "query": _QUERY,
        "variables": {"organizationHostedJobsPageName": slug},
    }
    resp = polite_post(_GRAPHQL_URL, json=body)
    if resp.status_code != 200:
        print(f"[ashby:{slug}] {resp.status_code} {resp.text[:200]}")
        return []
    payload = resp.json()
    board = (payload.get("data") or {}).get("jobBoard") or {}
    postings = board.get("jobPostings", []) or []
    out: list[JobModel] = []
    for p in postings:
        posting_id = p.get("id", "")
        out.append(
            JobModel(
                id=str(posting_id),
                title=p.get("title", ""),
                location=p.get("locationName", "") or "",
                description_md="",
                apply_url=f"https://jobs.ashbyhq.com/{slug}/{posting_id}",
                raw=p,
            )
        )
    return out


def fetch_description(slug: str, posting_id: str) -> str:
    """Lazily fetch a single posting's description in markdown."""
    query = """
    query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
      jobPosting(
        organizationHostedJobsPageName: $organizationHostedJobsPageName
        jobPostingId: $jobPostingId
      ) { descriptionHtml }
    }
    """.strip()
    body = {
        "operationName": "ApiJobPosting",
        "query": query,
        "variables": {
            "organizationHostedJobsPageName": slug,
            "jobPostingId": posting_id,
        },
    }
    resp = polite_post(
        "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting",
        json=body,
    )
    if resp.status_code != 200:
        return ""
    posting = (resp.json().get("data") or {}).get("jobPosting") or {}
    raw_html = html.unescape(posting.get("descriptionHtml") or "")
    return html_to_markdown(raw_html)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "linqapp"
    jobs = list_jobs(target)
    print(f"{target}: {len(jobs)} open roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
