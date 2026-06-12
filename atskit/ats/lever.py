"""Lever public postings API."""

from __future__ import annotations

from .base import JobModel, polite_get


def list_jobs(slug: str) -> list[JobModel]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    resp = polite_get(url)
    if resp.status_code != 200:
        print(f"[lever:{slug}] {resp.status_code} {resp.text[:200]}")
        return []
    data = resp.json()
    out: list[JobModel] = []
    for item in data:
        categories = item.get("categories", {}) or {}
        location = categories.get("location") or categories.get("allLocations", [""])[0] or ""
        # Ensure country is in raw if available
        if "country" not in item and "country" in categories:
            item["country"] = categories["country"]
        description = item.get("descriptionPlain") or item.get("description") or ""
        out.append(
            JobModel(
                id=str(item.get("id", "")),
                title=item.get("text", ""),
                location=str(location),
                description_md=description,
                apply_url=item.get("hostedUrl") or item.get("applyUrl") or "",
                raw=item,
            )
        )
    return out


def fetch_description(slug: str, job_id: str) -> str:
    url = f"https://api.lever.co/v0/postings/{slug}/{job_id}"
    resp = polite_get(url)
    if resp.status_code != 200:
        return ""
    item = resp.json()
    return item.get("descriptionPlain") or item.get("description") or ""


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "netflix"
    jobs = list_jobs(target)
    print(f"{target}: {len(jobs)} open roles")
    for j in jobs[:5]:
        print(f"  - {j.title} | {j.location}")
