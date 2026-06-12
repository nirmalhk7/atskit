"""Amazon Jobs public search API."""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlencode

from .base import browser_headers, JobModel, html_to_markdown, polite_get


_SEARCH_URL = "https://amazon.jobs/en/search.json"
_PUBLIC_ROOT = "https://amazon.jobs"
_QUERY = "Software Engineer"
_LOCATION = "United States"
_COUNTRY = "USA"
_PAGE_SIZE = 100
_MAX_RESULTS = 200
_RADIUS = "24km"
_SORT = "recent"
SKIP_RESUME_BUILD = True


def _search_params(base_query: str = _QUERY, offset: int = 0) -> dict[str, Any]:
    return {
        "base_query": base_query,
        "loc_query": _LOCATION,
        "country": _COUNTRY,
        "latitude": "",
        "longitude": "",
        "radius": _RADIUS,
        "sort": _SORT,
        "result_limit": _PAGE_SIZE,
        "offset": offset,
    }


def _headers(referer: str) -> dict[str, str]:
    return browser_headers(referer, accept="application/json, text/plain, */*")


def _search_referer(base_query: str = _QUERY) -> str:
    params = {
        "base_query": base_query,
        "loc_query": _LOCATION,
        "country": _COUNTRY,
        "radius": _RADIUS,
        "sort": _SORT,
    }
    return f"https://amazon.jobs/en/search?{urlencode(params)}"


def _get_json(url: str, *, base_query: str = _QUERY):
    return polite_get(url, headers=_headers(_search_referer(base_query)))


def _search_url(base_query: str = _QUERY, offset: int = 0) -> str:
    return f"{_SEARCH_URL}?{urlencode(_search_params(base_query, offset))}"


def _path_job_id(job_path: str) -> str:
    match = re.search(r"/jobs/([^/]+)", job_path or "")
    return match.group(1) if match else ""


def _job_id(item: dict[str, Any]) -> str:
    for key in ("id_icims", "id", "job_id", "jobId"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return _path_job_id(str(item.get("job_path") or ""))


def _public_url(item: dict[str, Any]) -> str:
    path = str(item.get("job_path") or "").strip()
    if path.startswith("http"):
        return path
    if path:
        return f"{_PUBLIC_ROOT}{path if path.startswith('/') else '/' + path}"
    job_id = _job_id(item)
    return f"{_PUBLIC_ROOT}/en/jobs/{job_id}" if job_id else ""


def _location_from_locations(locations: Any) -> str:
    if not isinstance(locations, list):
        return ""
    names: list[str] = []
    for loc in locations:
        if isinstance(loc, str):
            name = loc.strip()
        elif isinstance(loc, dict):
            name = str(
                loc.get("display_name")
                or loc.get("normalized_location")
                or loc.get("name")
                or loc.get("city")
                or ""
            ).strip()
            region = str(loc.get("state") or loc.get("region") or "").strip()
            if name and region and region not in name:
                name = f"{name}, {region}"
        else:
            continue
        if name and name not in names:
            names.append(name)
    return ", ".join(names)


def _location(item: dict[str, Any]) -> str:
    for key in ("location", "normalized_location", "locations_text", "locationsText"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    locations = _location_from_locations(item.get("locations"))
    if locations:
        return locations
    parts = [str(item.get(key) or "").strip() for key in ("city", "state", "country_code")]
    return ", ".join(part for part in parts if part)


def _markdown_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        lines = []
        for item in value:
            text = _markdown_value(item)
            if text:
                lines.append(f"- {text}" if "\n" not in text else text)
        return "\n".join(lines).strip()
    if isinstance(value, dict):
        return _markdown_value(value.get("text") or value.get("content") or value.get("description") or "")
    text = html_to_markdown(html.unescape(str(value))).strip()
    return re.sub(r"(?<!\\)\+", r"\+", text) if text else text


def _section(title: str, value: Any) -> str:
    text = _markdown_value(value)
    return f"## {title}\n\n{text}" if text else ""


def _description_md(item: dict[str, Any]) -> str:
    sections = [
        _section("Description", item.get("description")),
        _section("Basic Qualifications", item.get("basic_qualifications")),
        _section("Preferred Qualifications", item.get("preferred_qualifications")),
    ]
    return "\n\n".join(section for section in sections if section).strip()


def _matches_id(item: dict[str, Any], job_id: str) -> bool:
    expected = str(job_id or "").strip()
    if not expected:
        return False
    candidates = {
        str(item.get("id_icims") or "").strip(),
        str(item.get("id") or "").strip(),
        str(item.get("job_id") or "").strip(),
        str(item.get("jobId") or "").strip(),
        _path_job_id(str(item.get("job_path") or "")),
    }
    next_step = str(item.get("url_next_step") or "")
    if next_step:
        candidates.add(_path_job_id(next_step))
        match = re.search(r"/jobs/([^/]+)/apply", next_step)
        if match:
            candidates.add(match.group(1))
    return expected in candidates


def _map_job(item: dict[str, Any]) -> JobModel | None:
    amazon_id = _job_id(item)
    apply_url = _public_url(item)
    if not amazon_id or not apply_url:
        return None
    raw = dict(item)
    if raw.get("country") is None and item.get("country_code") is not None:
        raw["country"] = item.get("country_code")
    return JobModel(
        id=amazon_id,
        title=str(item.get("title") or item.get("normalized_title") or "").strip(),
        location=_location(item),
        description_md=_description_md(item),
        apply_url=apply_url,
        raw=raw,
    )


def list_jobs(slug: str) -> list[JobModel]:
    if slug != "amazon":
        return []

    out: list[JobModel] = []
    seen_ids: set[str] = set()
    offset = 0
    while offset < _MAX_RESULTS:
        resp = _get_json(_search_url(offset=offset))
        if resp.status_code != 200:
            print(f"[amazon] {resp.status_code} {resp.text[:200]}")
            return out

        payload = resp.json()
        jobs = payload.get("jobs") or []
        if not isinstance(jobs, list) or not jobs:
            break

        for item in jobs:
            if not isinstance(item, dict):
                continue
            job = _map_job(item)
            if not job or job.id in seen_ids:
                continue
            seen_ids.add(job.id)
            out.append(job)
            if len(out) >= _MAX_RESULTS:
                break

        hits = payload.get("hits")
        offset += _PAGE_SIZE
        if len(out) >= _MAX_RESULTS or len(jobs) < _PAGE_SIZE or (isinstance(hits, int) and offset >= hits):
            break
    return out


def fetch_description(slug: str, job_id: str) -> str:
    if slug != "amazon" or not job_id:
        return ""

    resp = _get_json(_search_url(str(job_id)), base_query=str(job_id))
    if resp.status_code != 200:
        return ""

    for item in resp.json().get("jobs") or []:
        if isinstance(item, dict) and _matches_id(item, str(job_id)):
            return _description_md(item)
    return ""


if __name__ == "__main__":
    jobs = list_jobs("amazon")
    print(f"amazon: {len(jobs)} US Software Engineer roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
