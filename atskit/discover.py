"""Streaming cross-portal job discovery."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

from .models import JobListing, PortalEntry, PortalJobsResult
from .persistence import PortalStore
from .registry import get_client


def _query_portal(entry: PortalEntry) -> tuple[list[JobListing], str | None]:
    client = get_client(entry.portal)
    if client is None:
        return [], f"unsupported portal: {entry.portal}"
    try:
        jobs = client.list_jobs(entry.slug)
        return jobs, None
    except Exception as exc:
        return [], str(exc)


def discover_jobs(
    db_path: Path | str,
    *,
    skip_scanned_today: bool = True,
    max_workers: int = 3,
    portals: list[str] | None = None,
    mark_scanned: bool = True,
) -> Iterator[PortalJobsResult]:
    """Yield one PortalJobsResult per portal as each ATS query completes."""
    store = PortalStore(db_path)
    entries = store.load()
    today = date.today().isoformat()

    if skip_scanned_today:
        entries = [entry for entry in entries if entry.last_scanned_date != today]
    if portals:
        allowed = set(portals)
        entries = [entry for entry in entries if entry.portal in allowed]

    if not entries:
        return

    max_workers = max(1, min(max_workers, len(entries)))
    last_portal: str | None = None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_entry = {
            pool.submit(_query_portal, entry): entry for entry in entries
        }
        for future in as_completed(future_to_entry):
            entry = future_to_entry[future]
            if entry.portal == "greenhouse" and last_portal == "greenhouse":
                time.sleep(random.uniform(1.0, 3.0))
            last_portal = entry.portal

            started = time.perf_counter()
            jobs, error = future.result()
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = PortalJobsResult(
                entry=entry,
                jobs=jobs,
                error=error,
                duration_ms=duration_ms,
                scanned_at=datetime.now(timezone.utc),
            )
            if mark_scanned and error is None:
                store.mark_scanned_today(entry.name)
            yield result
