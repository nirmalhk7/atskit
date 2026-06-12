"""ATSKit — discover jobs across ATS portals."""

from __future__ import annotations

from pathlib import Path

from .discover import discover_jobs
from .models import (
    FetchDescriptionResult,
    JobListing,
    PortalClassification,
    PortalEntry,
    PortalJobsResult,
)
from .persistence import PortalStore
from .portal_map import build_portals, load_portals, sync_portals_from_applied
from .registry import CLIENTS, SUPPORTED_PORTALS, get_client
from .service import fetch_description, fetch_description_for_url, list_jobs, list_jobs_for_entry
from .url import URLUtility, classify_url, clean_url

__all__ = [
    "CLIENTS",
    "SUPPORTED_PORTALS",
    "URLUtility",
    "PortalStore",
    "PortalEntry",
    "PortalClassification",
    "PortalJobsResult",
    "JobListing",
    "FetchDescriptionResult",
    "discover_jobs",
    "load_portals",
    "build_portals",
    "sync_portals_from_applied",
    "list_jobs",
    "list_jobs_for_entry",
    "fetch_description",
    "fetch_description_for_url",
    "classify_url",
    "clean_url",
    "get_client",
]
