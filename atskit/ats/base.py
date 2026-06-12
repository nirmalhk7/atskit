"""Compatibility shim: ATS modules import from here."""

from __future__ import annotations

from typing import Protocol

from ..http import (
    BROWSER_HEADER_PROFILES,
    browser_headers,
    html_to_markdown,
    polite_get,
    polite_post,
)
from ..models import JobListing as JobModel


class ATSClient(Protocol):
    def list_jobs(self, slug: str) -> list[JobModel]: ...


__all__ = [
    "ATSClient",
    "BROWSER_HEADER_PROFILES",
    "JobModel",
    "browser_headers",
    "html_to_markdown",
    "polite_get",
    "polite_post",
]
