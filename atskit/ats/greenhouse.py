"""Greenhouse public boards API."""

from __future__ import annotations

import html

try:
    import trafilatura
except ImportError:
    trafilatura = None

from .base import JobModel, html_to_markdown, polite_get


def _clean_html(content: str) -> str:
    if trafilatura is not None:
        return trafilatura.extract(content) or content
    return html_to_markdown(content)


def _log_error(slug: str, resp) -> None:
    print(f"[greenhouse portal=greenhouse slug={slug}] {resp.status_code} {resp.text[:200]}")


def list_jobs(slug: str) -> list[JobModel]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    resp = polite_get(url)
    if resp.status_code != 200:
        _log_error(slug, resp)
        return []
    data = resp.json()
    out: list[JobModel] = []
    for item in data.get("jobs", []):
        content = html.unescape(item.get("content") or "")
        description_md = _clean_html(content)
        out.append(
            JobModel(
                id=str(item.get("id", "")),
                title=item.get("title", ""),
                location=(item.get("location") or {}).get("name", "") or (item.get("offices", [{}])[0].get("name", "")),
                description_md=description_md or "",
                apply_url=item.get("absolute_url", ""),
                raw=item,
            )
        )
    return out


def fetch_description(slug: str, job_id: str) -> str:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}?content=true"
    resp = polite_get(url)
    if resp.status_code != 200:
        _log_error(slug, resp)
        return ""
    data = resp.json()
    content = html.unescape(data.get("content") or "")
    return _clean_html(content)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "stripe"
    jobs = list_jobs(target)
    print(f"{target}: {len(jobs)} open roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
