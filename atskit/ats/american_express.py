"""American Express Oracle HCM Candidate Experience API client."""

from __future__ import annotations

import random
import re
import time
from typing import Any
from urllib.parse import urlencode

from .base import browser_headers, JobModel, html_to_markdown, polite_get


_API_ROOT = "https://egug.fa.us2.oraclecloud.com/hcmRestApi/resources/latest"
_SEARCH_URL = f"{_API_ROOT}/recruitingCEJobRequisitions"
_DETAIL_URL = f"{_API_ROOT}/recruitingCEJobRequisitionDetails"
_PUBLIC_DETAIL_URL = "https://careers.americanexpress.com/en/sites/CX_1/job/{job_id}"
_SEARCH_REFERER = (
    "https://careers.americanexpress.com/en/sites/CX_1/jobs"
    "?keyword=Software%20Engineer&location=United%20States"
)
_SITE_NUMBER = "CX_1"
_QUERY = "Software Engineer"
_US_LOCATION_ID = "300000000229164"
_CAREER_AREA_FACET = "AttributeChar6|Technology"
_POSTING_DATES_FACET = "30"
_LIMIT = 10
_PAGE_PAUSE_RANGE_S = (0.4, 1.2)


def _headers(referer: str) -> dict[str, str]:
    return browser_headers(
        referer,
        origin="https://careers.americanexpress.com",
        accept="application/json, text/plain, */*",
        sec_fetch_site="cross-site",
        sec_fetch_mode="cors",
        sec_fetch_dest="empty",
        connection="keep-alive",
    )


def _pause_between_pages() -> None:
    time.sleep(random.uniform(*_PAGE_PAUSE_RANGE_S))


def _search_finder(offset: int) -> str:
    parts = [
        ("siteNumber", _SITE_NUMBER),
        ("keyword", _QUERY),
        ("selectedLocationsFacet", _US_LOCATION_ID),
        ("selectedFlexFieldsFacets", _CAREER_AREA_FACET),
        ("selectedPostingDatesFacet", _POSTING_DATES_FACET),
        ("sortBy", "RELEVANCY"),
        ("limit", _LIMIT),
        ("offset", offset),
    ]
    return "findReqs;" + ",".join(f"{key}={value}" for key, value in parts)


def _search_url(offset: int) -> str:
    params = [
        ("onlyData", "true"),
        ("expand", "requisitionList.secondaryLocations"),
        ("finder", _search_finder(offset)),
    ]
    return f"{_SEARCH_URL}?{urlencode(params)}"


def _detail_url(job_id: str) -> str:
    finder = f'ById;Id="{job_id}",siteNumber={_SITE_NUMBER}'
    params = [
        ("expand", "all"),
        ("onlyData", "true"),
        ("finder", finder),
    ]
    return f"{_DETAIL_URL}?{urlencode(params)}"


def _search_item(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        return items[0]
    return payload


def _detail_item(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        return items[0]
    return payload


def _job_id(item: dict[str, Any]) -> str:
    return str(item.get("Id") or item.get("id") or item.get("RequisitionNumber") or "").strip()


def _deduped_locations(item: dict[str, Any]) -> str:
    names: list[str] = []
    primary = str(item.get("PrimaryLocation") or "").strip()
    if primary:
        names.append(primary)
    for loc in item.get("secondaryLocations") or []:
        if not isinstance(loc, dict):
            continue
        name = str(loc.get("Name") or loc.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return ", ".join(names)


def _map_job(item: dict[str, Any]) -> JobModel | None:
    amex_id = _job_id(item)
    if not amex_id:
        return None

    raw = {
        "postedDate": item.get("PostedDate"),
        "postingEndDate": item.get("PostingEndDate"),
        "primaryLocationCountry": item.get("PrimaryLocationCountry"),
        "category": item.get("Category"),
        "jobFunction": item.get("JobFunction"),
        "workplaceType": item.get("WorkplaceType"),
        "workplaceTypeCode": item.get("WorkplaceTypeCode"),
        "secondaryLocations": item.get("secondaryLocations") or [],
        "country": item.get("PrimaryLocationCountry") or "US",
    }
    return JobModel(
        id=amex_id,
        title=str(item.get("Title") or "").strip(),
        location=_deduped_locations(item),
        description_md="",
        apply_url=_PUBLIC_DETAIL_URL.format(job_id=amex_id),
        raw=raw,
    )


def list_jobs(slug: str) -> list[JobModel]:
    if slug != "american_express":
        return []

    out: list[JobModel] = []
    seen_ids: set[str] = set()
    offset = 0
    total_count: int | None = None
    headers = _headers(_SEARCH_REFERER)

    while True:
        resp = polite_get(_search_url(offset), headers=headers)
        if resp.status_code != 200:
            print(f"[american_express] {resp.status_code} {resp.text[:200]}")
            return out

        data = _search_item(resp.json())
        requisitions = data.get("requisitionList") or []
        if not isinstance(requisitions, list) or not requisitions:
            break

        raw_total = data.get("TotalJobsCount")
        if isinstance(raw_total, int):
            total_count = raw_total

        for item in requisitions:
            if not isinstance(item, dict):
                continue
            amex_id = _job_id(item)
            if not amex_id or amex_id in seen_ids:
                continue
            seen_ids.add(amex_id)
            job = _map_job(item)
            if job:
                out.append(job)

        offset += _LIMIT
        if total_count is not None and offset >= total_count:
            break
        _pause_between_pages()

    return out


def _section(title: str, value: Any) -> str:
    text = html_to_markdown(str(value or "")).strip()
    text = re.sub(r"(?<=\d)-(?=\d)", r"\-", text)
    return f"## {title}\n\n{text}" if text else ""


def _salary_sections(item: dict[str, Any]) -> list[str]:
    sections: list[str] = []
    for field in item.get("requisitionFlexFields") or []:
        if not isinstance(field, dict):
            continue
        prompt = str(field.get("Prompt") or "").strip()
        value = str(field.get("Value") or "").strip()
        if not prompt or not value:
            continue
        if any(term in prompt.lower() for term in ("salary", "compensation", "pay")):
            sections.append(f"## {prompt}\n\n{value}")
    return sections


def fetch_description(slug: str, job_id: str) -> str:
    if slug != "american_express" or not job_id:
        return ""

    detail_url = _PUBLIC_DETAIL_URL.format(job_id=job_id)
    resp = polite_get(_detail_url(job_id), headers=_headers(detail_url))
    if resp.status_code != 200:
        return ""

    item = _detail_item(resp.json())
    sections = [
        _section("Description", item.get("ExternalDescriptionStr")),
        _section("Responsibilities", item.get("ExternalResponsibilitiesStr")),
        _section("Qualifications", item.get("ExternalQualificationsStr")),
        _section("About American Express", item.get("CorporateDescriptionStr")),
        _section("Benefits", item.get("OrganizationDescriptionStr")),
        *_salary_sections(item),
    ]
    return "\n\n".join(section for section in sections if section).strip()


if __name__ == "__main__":
    jobs = list_jobs("american_express")
    print(f"american_express: {len(jobs)} recent US Technology Software Engineer roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
