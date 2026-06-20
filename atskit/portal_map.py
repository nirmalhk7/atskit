"""Build and load portal metadata from a caller-supplied SQLite DB."""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .models import PortalEntry
from .persistence import PortalStore
from .url import (
    AMAZON,
    AMERICAN_EXPRESS,
    APPLE,
    MICROSOFT,
    SUPPORTED_PORTALS,
    WORKDAY,
    classify_url,
)

AppliedJobsProvider = Callable[[], list[dict[str, Any]]]

_BUILTIN_ENTRIES = [
    PortalEntry(
        name="Apple",
        slug="apple",
        portal=APPLE,
        sample_url="https://jobs.apple.com/en-us/search",
    ),
    PortalEntry(
        name="Amazon",
        slug="amazon",
        portal=AMAZON,
        sample_url="https://amazon.jobs/en/search",
    ),
    PortalEntry(
        name="Microsoft",
        slug="microsoft",
        portal=MICROSOFT,
        sample_url="https://apply.careers.microsoft.com/careers",
    ),
    PortalEntry(
        name="American Express",
        slug="american_express",
        portal=AMERICAN_EXPRESS,
        sample_url="https://careers.americanexpress.com/en/sites/CX_1/jobs",
    ),
]

_FIXED_PORTALS = {WORKDAY, APPLE, AMAZON, MICROSOFT, AMERICAN_EXPRESS}


def _builtin_keys() -> set[tuple[str, str]]:
    return {(entry.portal, entry.slug.lower()) for entry in _BUILTIN_ENTRIES}


def _canonical_company(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).title()


def _merge_company(existing: dict[str, PortalEntry], name: str) -> str:
    canon = _canonical_company(name)
    if canon in existing:
        return canon
    for key in existing:
        if fuzz.ratio(canon.lower(), key.lower()) >= 90:
            return key
    return canon


def _job_url(job: dict[str, Any]) -> str:
    return (
        job.get("job_link")
        or job.get("jobLink")
        or job.get("url")
        or ""
    )


def _job_company(job: dict[str, Any]) -> str:
    return (
        job.get("company_name")
        or job.get("company")
        or job.get("Company")
        or ""
    )


def _with_builtin_entries(entries: list[PortalEntry]) -> list[PortalEntry]:
    merged = list(entries)
    keys = {(entry.portal, entry.slug.lower()) for entry in merged}
    for entry in _BUILTIN_ENTRIES:
        key = (entry.portal, entry.slug.lower())
        if key not in keys:
            merged.append(entry)
            keys.add(key)
    return merged


def _save(store: PortalStore, entries: list[PortalEntry]) -> None:
    store.replace(_with_builtin_entries(entries))


def load_portals(db_path: Path | str) -> list[PortalEntry]:
    store = PortalStore(db_path)
    entries = [e for e in store.load() if e.portal in SUPPORTED_PORTALS]
    entries = _with_builtin_entries(entries)
    _ensure_builtin_entries_persisted(store, entries)
    random.shuffle(entries)
    return entries


def _ensure_builtin_entries_persisted(store: PortalStore, entries: list[PortalEntry]) -> None:
    existing_keys = {(entry.portal, entry.slug.lower()) for entry in store.load()}
    missing = [
        entry
        for entry in _BUILTIN_ENTRIES
        if (entry.portal, entry.slug.lower()) not in existing_keys
    ]
    if missing:
        store.replace(entries)


def build_portals(
    db_path: Path | str,
    *,
    applied_jobs: AppliedJobsProvider | None = None,
    force_refresh: bool = False,
) -> list[PortalEntry]:
    store = PortalStore(db_path)
    current_entries = load_portals(db_path)
    current_statuses = {entry.name: entry.status for entry in current_entries}
    has_non_builtin_entries = any(
        (entry.portal, entry.slug.lower()) not in _builtin_keys()
        for entry in current_entries
    )
    if not force_refresh and has_non_builtin_entries:
        return current_entries

    if applied_jobs is None:
        entries = sorted(_with_builtin_entries(current_entries), key=lambda e: e.name.lower())
        _save(store, entries)
        random.shuffle(entries)
        return entries

    preserved_fixed = [e for e in current_entries if e.portal in _FIXED_PORTALS]
    applied = applied_jobs()

    companies: dict[str, PortalEntry] = {}
    skipped = 0
    for job in applied:
        url = _job_url(job)
        company = _job_company(job)
        if not company or not url:
            continue
        classified = classify_url(url)
        if classified is None:
            skipped += 1
            continue
        key = _merge_company(companies, company)
        companies.setdefault(
            key,
            PortalEntry(
                name=key,
                slug=classified.slug,
                portal=classified.portal,
                sample_url=url,
                status=current_statuses.get(key, True),
            ),
        )

    existing_portal_keys = {(e.portal, e.slug.lower()) for e in companies.values()}
    for entry in preserved_fixed:
        key = _merge_company(companies, entry.name)
        portal_key = (entry.portal, entry.slug.lower())
        if portal_key not in existing_portal_keys:
            companies.setdefault(key, entry)
            existing_portal_keys.add(portal_key)

    entries = sorted(companies.values(), key=lambda e: e.name.lower())
    print(
        f"[portal_map] Kept {len(entries)} companies on supported ATS portals; "
        f"dropped {skipped} on other portals."
    )
    _save(store, entries)
    random.shuffle(entries)
    return entries


def sync_portals_from_applied(
    db_path: Path | str,
    applied_jobs: AppliedJobsProvider,
) -> int:
    store = PortalStore(db_path)
    existing = {entry.name: entry for entry in load_portals(db_path)}
    existing_portal_keys = {(e.portal, e.slug.lower()) for e in existing.values()}

    applied = applied_jobs()
    found_new: list[PortalEntry] = []
    for job in applied:
        url = _job_url(job)
        company = _job_company(job)
        if not company or not url:
            continue
        classified = classify_url(url)
        if classified is None:
            continue
        portal_key = (classified.portal, classified.slug.lower())
        if portal_key in existing_portal_keys:
            continue

        key = _merge_company(existing, company)
        if key in existing:
            if (existing[key].portal, existing[key].slug.lower()) == portal_key:
                continue

        new_entry = PortalEntry(
            name=key,
            slug=classified.slug,
            portal=classified.portal,
            sample_url=url,
            status=existing[key].status if key in existing else True,
        )
        found_new.append(new_entry)
        existing[key] = new_entry
        existing_portal_keys.add(portal_key)

    if not found_new:
        return 0

    merged = sorted(existing.values(), key=lambda e: e.name.lower())
    _save(store, merged)
    return len(found_new)
