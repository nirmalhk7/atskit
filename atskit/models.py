"""Structured response models for ATSKit."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, computed_field


class JobListing(BaseModel):
    id: str
    title: str
    location: str
    description_md: str
    apply_url: str
    raw: dict[str, Any] = Field(default_factory=dict)


# Backward-compatible alias used by ATS client modules.
JobModel = JobListing


class PortalEntry(BaseModel):
    name: str
    slug: str
    portal: str
    sample_url: str
    last_scanned_date: str = ""
    status: bool = True

    model_config = {"frozen": True}


class PortalClassification(BaseModel):
    portal: str
    slug: str
    job_id: str


class PortalJobsResult(BaseModel):
    entry: PortalEntry
    jobs: list[JobListing] = Field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def job_count(self) -> int:
        return len(self.jobs)


class FetchDescriptionResult(BaseModel):
    portal: str
    slug: str
    job_id: str
    description_md: str = ""
    error: str | None = None
