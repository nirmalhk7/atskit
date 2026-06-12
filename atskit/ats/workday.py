"""Workday CXS public job board API."""

from __future__ import annotations

import html
import random
import time
from dataclasses import dataclass

from .base import (
    BROWSER_HEADER_PROFILES as _BROWSER_HEADER_PROFILES,
    JobModel,
    browser_headers,
    html_to_markdown,
    polite_get,
    polite_post,
)


_PAGE_SIZE = 20
_PAGE_PAUSE_RANGE_S = (1.5, 4.0)
_HEADER_PROFILES = _BROWSER_HEADER_PROFILES


@dataclass(frozen=True)
class WorkdayBoard:
    host: str
    tenant: str
    site: str


def _parse_slug(slug: str) -> WorkdayBoard:
    parts = (slug or "").split("|")
    if len(parts) != 3 or not all(parts):
        raise ValueError("Workday slug must be 'host|tenant|site'")
    host, tenant, site = parts
    host = host.removeprefix("https://").removeprefix("http://").strip("/")
    return WorkdayBoard(host=host, tenant=tenant, site=site)


def _list_url(board: WorkdayBoard) -> str:
    return f"https://{board.host}/wday/cxs/{board.tenant}/{board.site}/jobs"


def _detail_url(board: WorkdayBoard, external_path: str) -> str:
    path = external_path if external_path.startswith("/") else f"/{external_path}"
    return f"https://{board.host}/wday/cxs/{board.tenant}/{board.site}{path}"


def _public_url(board: WorkdayBoard, external_path: str) -> str:
    path = external_path if external_path.startswith("/") else f"/{external_path}"
    return f"https://{board.host}/en-US/{board.site}{path}"


def _headers(board: WorkdayBoard, *, json: bool = False) -> dict[str, str]:
    return browser_headers(
        f"https://{board.host}/en-US/{board.site}",
        origin=f"https://{board.host}",
        content_type="application/json" if json else None,
    )


def _pause_between_pages() -> None:
    time.sleep(random.uniform(*_PAGE_PAUSE_RANGE_S))


def _job_id(posting: dict) -> str:
    bullet_fields = posting.get("bulletFields") or []
    if bullet_fields:
        return str(bullet_fields[0])
    external_path = str(posting.get("externalPath") or "")
    return external_path.rsplit("_", 1)[-1] or external_path.rsplit("/", 1)[-1]


def list_jobs(slug: str) -> list[JobModel]:
    board = _parse_slug(slug)
    out: list[JobModel] = []
    seen_paths: set[str] = set()
    offset = 0
    total: int | None = None
    headers = _headers(board, json=True)

    while total is None or offset < total:
        body = {
            "appliedFacets": {},
            "limit": _PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }
        resp = polite_post(
            _list_url(board),
            json=body,
            headers=headers,
        )
        if resp.status_code != 200:
            print(f"[workday:{board.tenant}/{board.site}] {resp.status_code} {resp.text[:200]}")
            return out

        payload = resp.json()
        if total is None:
            total = int(payload.get("total") or 0)
        postings = payload.get("jobPostings") or []
        if not postings:
            break

        for posting in postings:
            external_path = str(posting.get("externalPath") or "")
            if not external_path or external_path in seen_paths:
                continue
            seen_paths.add(external_path)
            raw = dict(posting)
            raw["workday_slug"] = slug
            raw["externalPath"] = external_path
            out.append(
                JobModel(
                    id=_job_id(posting),
                    title=str(posting.get("title") or ""),
                    location=str(posting.get("locationsText") or ""),
                    description_md="",
                    apply_url=_public_url(board, external_path),
                    raw=raw,
                )
            )

        offset += len(postings)
        if len(postings) < _PAGE_SIZE:
            break
        if offset < total:
            _pause_between_pages()

    return out


def fetch_description(slug: str, job_id_or_external_path: str) -> str:
    if not job_id_or_external_path:
        return ""
    if not str(job_id_or_external_path).startswith("/job/"):
        return ""

    board = _parse_slug(slug)
    resp = polite_get(_detail_url(board, str(job_id_or_external_path)), headers=_headers(board))
    if resp.status_code != 200:
        return ""

    posting = (resp.json().get("jobPostingInfo") or {})
    raw_html = html.unescape(posting.get("jobDescription") or "")
    return html_to_markdown(raw_html)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "nvidia.wd5.myworkdayjobs.com|nvidia|NVIDIAExternalCareerSite"
    jobs = list_jobs(target)
    print(f"{target}: {len(jobs)} open roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
