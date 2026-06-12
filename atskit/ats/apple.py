"""Apple Jobs public search and detail API."""

from __future__ import annotations

import random
import re
import time
from typing import Any

from .base import browser_headers, JobModel, html_to_markdown, polite_get, polite_post


_SEARCH_URL = "https://jobs.apple.com/api/v1/search"
_DETAIL_URL = "https://jobs.apple.com/api/v1/jobDetails/{job_id}?locale=en-us"
_SEARCH_REFERER = "https://jobs.apple.com/en-us/search?location=united-states-USA&search=Software%20Engineer&sort=newest"
_PUBLIC_DETAIL_URL = "https://jobs.apple.com/en-us/details/{job_id}/{title_slug}"
_QUERY = "Software Engineer"
_LOCALE = "en-us"
_US_LOCATION_ID = "postLocation-USA"
_MAX_PAGES = 5
_PAGE_PAUSE_RANGE_S = (0.4, 1.2)
SKIP_RESUME_BUILD = True


def _headers(referer: str) -> dict[str, str]:
    return browser_headers(
        referer,
        origin="https://jobs.apple.com",
        accept="application/json, text/plain, */*",
        content_type="application/json",
        sec_fetch_site="same-origin",
        sec_fetch_mode="cors",
        sec_fetch_dest="empty",
        connection="keep-alive",
    )


def _pause_between_pages() -> None:
    time.sleep(random.uniform(*_PAGE_PAUSE_RANGE_S))


def _search_payload(page: int) -> dict[str, Any]:
    return {
        "query": _QUERY,
        "filters": {"locations": [_US_LOCATION_ID]},
        "page": page,
        "locale": _LOCALE,
        "sort": "newest",
        "format": {
            "longDate": "MMMM D, YYYY",
            "mediumDate": "MMM D, YYYY",
        },
    }


def _payload(data: dict[str, Any]) -> dict[str, Any]:
    inner = data.get("res")
    return inner if isinstance(inner, dict) else data


def _title_slug(title: str) -> str:
    slug = (title or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"(^-+)|(-+$)", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "job"


def _location_names(locations: Any) -> list[str]:
    if not isinstance(locations, list):
        return []
    names: list[str] = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        name = str(loc.get("name") or loc.get("city") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _country_code(locations: Any) -> str:
    if not isinstance(locations, list):
        return ""
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        country_id = str(loc.get("countryID") or loc.get("postLocationCountryID") or "")
        country_name = str(loc.get("countryName") or "")
        if country_id.endswith("USA") or "United States" in country_name:
            return "US"
    return ""


def _map_job(item: dict[str, Any]) -> JobModel | None:
    apple_id = str(item.get("id") or item.get("jobNumber") or item.get("reqId") or "").strip()
    if not apple_id:
        return None
    title = str(item.get("postingTitle") or item.get("title") or "").strip()
    transformed = str(item.get("transformedPostingTitle") or "").strip() or _title_slug(title)
    locations = item.get("locations") or item.get("localeLocation") or []
    raw = dict(item)
    raw["apple_id"] = apple_id
    raw["posting_date"] = item.get("postingDate") or item.get("postDateInGMT") or ""
    raw["team"] = item.get("team") or item.get("teamNames") or ""
    raw["type"] = item.get("type") or ""
    raw["locations"] = locations
    raw["country"] = _country_code(locations)
    return JobModel(
        id=apple_id,
        title=title,
        location=", ".join(_location_names(locations)),
        description_md="",
        apply_url=_PUBLIC_DETAIL_URL.format(job_id=apple_id, title_slug=transformed),
        raw=raw,
    )


def list_jobs(slug: str) -> list[JobModel]:
    if slug != "apple":
        return []

    out: list[JobModel] = []
    seen_ids: set[str] = set()
    headers = _headers(_SEARCH_REFERER)
    for page in range(1, _MAX_PAGES + 1):
        resp = polite_post(_SEARCH_URL, json=_search_payload(page), headers=headers)
        if resp.status_code != 200:
            print(f"[apple] {resp.status_code} {resp.text[:200]}")
            return out

        data = _payload(resp.json())
        results = data.get("searchResults") or []
        if not results:
            break

        for item in results:
            if not isinstance(item, dict):
                continue
            apple_id = str(item.get("id") or item.get("jobNumber") or item.get("reqId") or "").strip()
            if not apple_id or apple_id in seen_ids:
                continue
            seen_ids.add(apple_id)
            job = _map_job(item)
            if job:
                out.append(job)

        if page < _MAX_PAGES:
            _pause_between_pages()

    return out


def _plain_section(title: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return f"## {title}\n\n{text}"


def _footer_sections(posting: dict[str, Any]) -> list[str]:
    sections: list[str] = []
    for footer in posting.get("postingFooters") or []:
        if not isinstance(footer, dict):
            continue
        localizations = footer.get("localizations") or {}
        if not isinstance(localizations, dict):
            continue
        for entries in localizations.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                footer_type = str(entry.get("type") or "")
                if "EEO" in footer_type or "ACCESSIBILITY" in footer_type:
                    continue
                content = html_to_markdown(str(entry.get("content") or ""))
                if not content:
                    continue
                label = str(entry.get("label") or "").strip()
                sections.append(f"## {label}\n\n{content}" if label else content)
    return sections


def fetch_description(slug: str, job_id: str) -> str:
    if slug != "apple" or not job_id:
        return ""

    detail_url = _PUBLIC_DETAIL_URL.format(job_id=job_id, title_slug="job")
    resp = polite_get(
        _DETAIL_URL.format(job_id=job_id),
        headers=_headers(detail_url),
    )
    if resp.status_code != 200:
        return ""

    posting = _payload(resp.json())
    sections = [
        _plain_section("Summary", posting.get("jobSummary")),
        _plain_section("Description", posting.get("description")),
        _plain_section("Responsibilities", posting.get("responsibilities")),
        _plain_section("Minimum Qualifications", posting.get("minimumQualifications")),
        _plain_section("Preferred Qualifications", posting.get("preferredQualifications")),
    ]
    sections.extend(_footer_sections(posting))
    return "\n\n".join(section for section in sections if section).strip()


if __name__ == "__main__":
    jobs = list_jobs("apple")
    print(f"apple: {len(jobs)} newest US Software Engineer roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
