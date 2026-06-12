"""Microsoft Careers public PCS search and detail API."""

from __future__ import annotations

import random
import time
from typing import Any
from urllib.parse import urlencode

from .base import browser_headers, JobModel, html_to_markdown, polite_get


_SEARCH_URL = "https://apply.careers.microsoft.com/api/pcsx/search"
_DETAIL_URL = "https://apply.careers.microsoft.com/api/pcsx/position_details"
_SEARCH_REFERER = (
    "https://apply.careers.microsoft.com/careers?"
    "query=Software%20Engineer&location=United%20States"
)
_PUBLIC_DETAIL_URL = "https://apply.careers.microsoft.com/careers/job/{job_id}"
_DOMAIN = "microsoft.com"
SKIP_RESUME_BUILD = True
_QUERY = "Software Engineer"
_LOCATION = "United States"
_PAGE_PAUSE_RANGE_S = (0.4, 1.2)
_SEARCH_FILTERS: dict[str, list[str]] = {
    "include_remote": ["1"],
    "profession": ["software engineering"],
    "seniority": ["Entry", "Mid-Level"],
}


def _headers(referer: str) -> dict[str, str]:
    return browser_headers(
        referer,
        origin="https://apply.careers.microsoft.com",
        accept="application/json, text/plain, */*",
        content_type="application/json",
        sec_fetch_site="same-origin",
        sec_fetch_mode="cors",
        sec_fetch_dest="empty",
        connection="keep-alive",
    )


def _pause_between_pages() -> None:
    time.sleep(random.uniform(*_PAGE_PAUSE_RANGE_S))


def _params(start: int) -> list[tuple[str, str | int]]:
    params: list[tuple[str, str | int]] = [
        ("domain", _DOMAIN),
        ("query", _QUERY),
        ("location", _LOCATION),
        ("start", start),
    ]
    for name, values in _SEARCH_FILTERS.items():
        for value in values:
            params.append((f"filter_{name}", value))
    return params


def _search_url(start: int) -> str:
    return f"{_SEARCH_URL}?{urlencode(_params(start))}"


def _detail_url(job_id: str) -> str:
    return f"{_DETAIL_URL}?{urlencode({'position_id': job_id, 'domain': _DOMAIN, 'hl': 'en'})}"


def _payload(data: dict[str, Any]) -> dict[str, Any]:
    inner = data.get("data")
    return inner if isinstance(inner, dict) else data


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _location(item: dict[str, Any]) -> str:
    standardized = _string_list(item.get("standardizedLocations"))
    if standardized:
        return ", ".join(standardized)
    return ", ".join(_string_list(item.get("locations")))


def _job_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("positionId") or item.get("atsJobId") or "").strip()


def _map_job(item: dict[str, Any]) -> JobModel | None:
    microsoft_id = _job_id(item)
    if not microsoft_id:
        return None

    raw = {
        "displayJobId": item.get("displayJobId"),
        "atsJobId": item.get("atsJobId"),
        "postedTs": item.get("postedTs"),
        "department": item.get("department"),
        "workLocationOption": item.get("workLocationOption"),
        "locationFlexibility": item.get("locationFlexibility"),
        "country": "US",
    }
    return JobModel(
        id=microsoft_id,
        title=str(item.get("name") or item.get("title") or "").strip(),
        location=_location(item),
        description_md="",
        apply_url=_PUBLIC_DETAIL_URL.format(job_id=microsoft_id),
        raw=raw,
    )


def list_jobs(slug: str) -> list[JobModel]:
    if slug != "microsoft":
        return []

    out: list[JobModel] = []
    seen_ids: set[str] = set()
    start = 0
    total_count: int | None = None
    headers = _headers(_SEARCH_REFERER)

    while True:
        resp = polite_get(_search_url(start), headers=headers)
        if resp.status_code != 200:
            print(f"[microsoft] {resp.status_code} {resp.text[:200]}")
            return out

        data = _payload(resp.json())
        positions = data.get("positions") or []
        if not isinstance(positions, list) or not positions:
            break

        raw_count = data.get("count")
        total_count = raw_count if isinstance(raw_count, int) else total_count

        for item in positions:
            if not isinstance(item, dict):
                continue
            microsoft_id = _job_id(item)
            if not microsoft_id or microsoft_id in seen_ids:
                continue
            seen_ids.add(microsoft_id)
            job = _map_job(item)
            if job:
                out.append(job)

        start += len(positions)
        if total_count is not None and start >= total_count:
            break
        _pause_between_pages()

    return out


def fetch_description(slug: str, job_id: str) -> str:
    if slug != "microsoft" or not job_id:
        return ""

    detail_url = _PUBLIC_DETAIL_URL.format(job_id=job_id)
    resp = polite_get(_detail_url(job_id), headers=_headers(detail_url))
    if resp.status_code != 200:
        return ""

    posting = _payload(resp.json())
    return html_to_markdown(str(posting.get("jobDescription") or "")).strip()


if __name__ == "__main__":
    jobs = list_jobs("microsoft")
    print(f"microsoft: {len(jobs)} active US Software Engineer roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
