"""Shared HTTP helpers for ATS clients."""

from __future__ import annotations

import random
import threading
import time

import requests
from bs4 import BeautifulSoup

from .config import ATS_HOST_MIN_INTERVAL_S, ATS_MAX_RETRIES, ATS_RETRY_DELAY

_last_call_per_host: dict[str, float] = {}
_last_call_lock = threading.Lock()

BROWSER_HEADER_PROFILES: tuple[dict[str, str], ...] = (
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    },
)


def html_to_markdown(raw_html: str) -> str:
    """Convert ATS-provided HTML fragments to readable Markdown text."""
    content = raw_html or ""
    if not content:
        return ""
    try:
        from markdownify import markdownify as _markdownify

        text = _markdownify(content, heading_style="ATX", bullets="-")
    except Exception:
        soup = BeautifulSoup(content, "html.parser")
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                heading.insert_before("\n")
                heading.string = f"{'#' * level} {heading.get_text(' ', strip=True)}"
                heading.insert_after("\n")
        for item in soup.find_all("li"):
            item.string = f"- {item.get_text(' ', strip=True)}"
            item.insert_after("\n")
        for block in soup.find_all(["p", "div", "br"]):
            block.insert_after("\n")
        text = soup.get_text(separator="\n")
    lines = [line.rstrip() for line in text.splitlines()]
    compacted: list[str] = []
    blank = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not blank and compacted:
                compacted.append("")
            blank = True
            continue
        compacted.append(stripped)
        blank = False
    return "\n".join(compacted).strip()


def browser_headers(
    referer: str | None = None,
    *,
    origin: str | None = None,
    accept: str | None = None,
    content_type: str | None = None,
    sec_fetch_site: str | None = None,
    sec_fetch_mode: str | None = None,
    sec_fetch_dest: str | None = None,
    connection: str | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a browser-like header set with a randomized user agent."""
    headers = dict(random.choice(BROWSER_HEADER_PROFILES))
    if referer is not None:
        headers["Referer"] = referer
    if origin is not None:
        headers["Origin"] = origin
    if accept is not None:
        headers["Accept"] = accept
    if content_type is not None:
        headers["Content-Type"] = content_type
    if sec_fetch_site is not None:
        headers["Sec-Fetch-Site"] = sec_fetch_site
    if sec_fetch_mode is not None:
        headers["Sec-Fetch-Mode"] = sec_fetch_mode
    if sec_fetch_dest is not None:
        headers["Sec-Fetch-Dest"] = sec_fetch_dest
    if connection is not None:
        headers["Connection"] = connection
    if extra:
        headers.update(extra)
    return headers


def polite_get(url: str, **kwargs) -> requests.Response:
    """GET with a per-host rate cap and exponential backoff on 429/5xx."""
    return _polite("GET", url, **kwargs)


def polite_post(url: str, **kwargs) -> requests.Response:
    return _polite("POST", url, **kwargs)


def _polite(method: str, url: str, **kwargs) -> requests.Response:
    from urllib.parse import urlparse

    host = urlparse(url).netloc
    with _last_call_lock:
        last = _last_call_per_host.get(host, 0.0)
        delta = time.time() - last
        if delta < ATS_HOST_MIN_INTERVAL_S:
            time.sleep(ATS_HOST_MIN_INTERVAL_S - delta)
        _last_call_per_host[host] = time.time()

    delay = ATS_RETRY_DELAY
    resp: requests.Response | None = None
    for _attempt in range(ATS_MAX_RETRIES):
        resp = requests.request(method, url, timeout=kwargs.pop("timeout", 30), **kwargs)
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            time.sleep(delay + random.uniform(0, 0.4))
            delay = min(delay * 2, 16.0)
            continue
        return resp
    assert resp is not None
    return resp
