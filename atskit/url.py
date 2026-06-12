"""URL classification utilities."""

from __future__ import annotations

import re
import urllib.parse
from urllib.parse import urlparse

from .models import PortalClassification

GREENHOUSE = "greenhouse"
LEVER = "lever"
ASHBY = "ashby"
GEM = "gem"
WORKDAY = "workday"
APPLE = "apple"
AMAZON = "amazon"
MICROSOFT = "microsoft"
AMERICAN_EXPRESS = "american_express"
SUPPORTED_PORTALS = {
    GREENHOUSE,
    LEVER,
    ASHBY,
    GEM,
    WORKDAY,
    APPLE,
    AMAZON,
    MICROSOFT,
    AMERICAN_EXPRESS,
}

_GREENHOUSE_PATTERNS = [
    re.compile(r"^(?:job-)?boards\.greenhouse\.io$", re.I),
    re.compile(r"^(?:[a-z0-9-]+)\.greenhouse\.io$", re.I),
]
_LEVER_HOST = re.compile(r"^jobs\.(?:eu\.)?lever\.co$", re.I)
_ASHBY_HOST = re.compile(r"^jobs\.ashbyhq\.com$", re.I)
_GEM_HOST = re.compile(r"^jobs\.gem\.com$", re.I)
_WORKDAY_HOST = re.compile(r"^[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com$", re.I)
_APPLE_HOST = re.compile(r"^jobs\.apple\.com$", re.I)
_AMAZON_PUBLIC_HOST = re.compile(r"^amazon\.jobs$", re.I)
_AMAZON_APPLY_HOST = re.compile(r"^account\.amazon(?:\.com|\.jobs)$", re.I)
_MICROSOFT_APPLY_HOST = re.compile(r"^apply\.careers\.microsoft\.com$", re.I)
_MICROSOFT_JOBS_HOST = re.compile(r"^jobs\.careers\.microsoft\.com$", re.I)
_AMERICAN_EXPRESS_PUBLIC_HOST = re.compile(r"^careers\.americanexpress\.com$", re.I)
_AMERICAN_EXPRESS_ORACLE_HOST = re.compile(r"^egug\.fa\.us2\.oraclecloud\.com(?::443)?$", re.I)


def clean_url(url: str, preserve_query_domains: set[str] | None = None) -> str:
    """Remove query parameters unless the host is in preserve_query_domains."""
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    allowlist = preserve_query_domains or set()
    query = parsed.query if host in allowlist else ""
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment)
    )


def classify_url(url: str) -> PortalClassification | None:
    """Return portal classification for supported ATS URLs, else None."""
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    path_parts = [p for p in (parsed.path or "").split("/") if p]
    if not host or not path_parts:
        return None

    if _APPLE_HOST.match(host):
        if (
            len(path_parts) >= 3
            and re.fullmatch(r"[a-z]{2}-[a-z]{2}", path_parts[0], re.I)
            and path_parts[1] == "details"
        ):
            return PortalClassification(portal=APPLE, slug="apple", job_id=path_parts[2])

    if _AMAZON_PUBLIC_HOST.match(host):
        if len(path_parts) >= 4 and path_parts[1] == "jobs":
            return PortalClassification(portal=AMAZON, slug="amazon", job_id=path_parts[2])
    if _AMAZON_APPLY_HOST.match(host):
        if len(path_parts) >= 2 and path_parts[0] == "jobs":
            return PortalClassification(portal=AMAZON, slug="amazon", job_id=path_parts[1])

    if _MICROSOFT_APPLY_HOST.match(host):
        if len(path_parts) >= 3 and path_parts[:2] == ["careers", "job"]:
            return PortalClassification(portal=MICROSOFT, slug="microsoft", job_id=path_parts[2])
    if _MICROSOFT_JOBS_HOST.match(host):
        if len(path_parts) >= 4 and path_parts[:3] == ["global", "en", "job"]:
            return PortalClassification(portal=MICROSOFT, slug="microsoft", job_id=path_parts[3])

    if _AMERICAN_EXPRESS_PUBLIC_HOST.match(host):
        if len(path_parts) >= 5 and path_parts[:4] == ["en", "sites", "CX_1", "job"]:
            return PortalClassification(
                portal=AMERICAN_EXPRESS, slug="american_express", job_id=path_parts[4]
            )
    if _AMERICAN_EXPRESS_ORACLE_HOST.match(host):
        if len(path_parts) >= 7 and path_parts[:6] == [
            "hcmUI",
            "CandidateExperience",
            "en",
            "sites",
            "CX_1",
            "job",
        ]:
            return PortalClassification(
                portal=AMERICAN_EXPRESS, slug="american_express", job_id=path_parts[6]
            )

    if _WORKDAY_HOST.match(host):
        inferred_tenant = host.split(".")[0]
        if len(path_parts) >= 5 and path_parts[:2] == ["wday", "cxs"]:
            tenant = path_parts[2]
            site = path_parts[3]
            slug = f"{host}|{tenant}|{site}"
            if path_parts[4] == "job":
                return PortalClassification(
                    portal=WORKDAY, slug=slug, job_id="/" + "/".join(path_parts[4:])
                )
            return PortalClassification(portal=WORKDAY, slug=slug, job_id="")
        if len(path_parts) >= 2 and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", path_parts[0]):
            site = path_parts[1]
            slug = f"{host}|{inferred_tenant}|{site}"
            if len(path_parts) >= 3 and path_parts[2] == "job":
                return PortalClassification(
                    portal=WORKDAY, slug=slug, job_id="/" + "/".join(path_parts[2:])
                )
            return PortalClassification(portal=WORKDAY, slug=slug, job_id="")

    if _GEM_HOST.match(host):
        if len(path_parts) >= 2:
            return PortalClassification(portal=GEM, slug=path_parts[0], job_id=path_parts[1])
        return PortalClassification(portal=GEM, slug=path_parts[0], job_id="")

    if _ASHBY_HOST.match(host):
        if len(path_parts) >= 2:
            return PortalClassification(portal=ASHBY, slug=path_parts[0], job_id=path_parts[1])
        return PortalClassification(portal=ASHBY, slug=path_parts[0], job_id="")

    if _LEVER_HOST.match(host):
        if len(path_parts) >= 2:
            return PortalClassification(portal=LEVER, slug=path_parts[0], job_id=path_parts[1])
        return PortalClassification(portal=LEVER, slug=path_parts[0], job_id="")

    if any(p.match(host) for p in _GREENHOUSE_PATTERNS):
        slug = ""
        job_id = ""
        if host.endswith("greenhouse.io") and host.split(".")[0] not in {"boards", "job-boards"}:
            slug = host.split(".")[0]
            if "jobs" in path_parts:
                idx = path_parts.index("jobs")
                if idx + 1 < len(path_parts):
                    job_id = path_parts[idx + 1]
        else:
            slug = path_parts[0]
            if "jobs" in path_parts:
                idx = path_parts.index("jobs")
                if idx + 1 < len(path_parts):
                    job_id = path_parts[idx + 1]
        if slug:
            return PortalClassification(portal=GREENHOUSE, slug=slug, job_id=job_id)

    return None


class URLUtility:
    """Compatibility wrapper exposing module-level URL helpers as a class."""

    GREENHOUSE = GREENHOUSE
    LEVER = LEVER
    ASHBY = ASHBY
    GEM = GEM
    WORKDAY = WORKDAY
    APPLE = APPLE
    AMAZON = AMAZON
    MICROSOFT = MICROSOFT
    AMERICAN_EXPRESS = AMERICAN_EXPRESS
    SUPPORTED_PORTALS = SUPPORTED_PORTALS

    @staticmethod
    def clean_url(url: str, preserve_query_domains: set[str] | None = None) -> str:
        return clean_url(url, preserve_query_domains)

    @classmethod
    def classify_portal(cls, url: str) -> tuple[str, str, str] | None:
        result = classify_url(url)
        if result is None:
            return None
        return result.portal, result.slug, result.job_id
