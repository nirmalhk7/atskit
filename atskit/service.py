"""Lower-level ATS query primitives."""

from __future__ import annotations

from .models import FetchDescriptionResult, JobListing, PortalEntry
from .registry import CLIENTS, get_client
from .url import classify_url


def list_jobs(portal: str, slug: str) -> list[JobListing]:
    client = get_client(portal)
    if client is None:
        return []
    return client.list_jobs(slug)


def list_jobs_for_entry(entry: PortalEntry) -> list[JobListing]:
    return list_jobs(entry.portal, entry.slug)


def fetch_description(portal: str, slug: str, job_id: str) -> FetchDescriptionResult:
    client = get_client(portal)
    if client is None:
        return FetchDescriptionResult(
            portal=portal,
            slug=slug,
            job_id=job_id,
            error=f"unsupported portal: {portal}",
        )
    if not hasattr(client, "fetch_description"):
        return FetchDescriptionResult(
            portal=portal,
            slug=slug,
            job_id=job_id,
            error="portal does not support fetch_description",
        )
    try:
        description_md = client.fetch_description(slug, job_id)
        return FetchDescriptionResult(
            portal=portal,
            slug=slug,
            job_id=job_id,
            description_md=description_md or "",
        )
    except Exception as exc:
        return FetchDescriptionResult(
            portal=portal,
            slug=slug,
            job_id=job_id,
            error=str(exc),
        )


def fetch_description_for_url(url: str) -> FetchDescriptionResult | None:
    classified = classify_url(url)
    if classified is None:
        return None
    lookup_id = classified.job_id
    if not lookup_id:
        return FetchDescriptionResult(
            portal=classified.portal,
            slug=classified.slug,
            job_id="",
            error="could not extract job id from url",
        )
    return fetch_description(classified.portal, classified.slug, lookup_id)


__all__ = [
    "CLIENTS",
    "list_jobs",
    "list_jobs_for_entry",
    "fetch_description",
    "fetch_description_for_url",
]
