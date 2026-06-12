# HTTP and rate limits

All ATS clients should route HTTP through `atskit.http` rather than calling `requests` directly. This keeps behavior consistent and reduces the chance of getting blocked.

## `polite_get` / `polite_post`

```python
from atskit.http import polite_get, polite_post

resp = polite_get("https://boards-api.greenhouse.io/v1/boards/acme/jobs")
resp = polite_post(url, json=payload, headers=headers)
```

### Per-host spacing

Before each request, ATSKit enforces a minimum interval per host (default **3 seconds**). If the last call to `boards-api.greenhouse.io` was 1s ago, the client sleeps 2s.

Configured in `atskit.config`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `ATS_HOST_MIN_INTERVAL_S` | `3.0` | Minimum seconds between requests to the same host |
| `ATS_MAX_RETRIES` | `5` | Max attempts on retryable failures |
| `ATS_RETRY_DELAY` | `1.0` | Initial backoff seconds (doubles up to 16s) |

### Retries

On **429** or **5xx** responses, the client sleeps with exponential backoff (+ small jitter) and retries. Non-retryable status codes return immediately.

### Timeouts

Default request timeout is **30 seconds** per attempt.

## Browser-like headers

`browser_headers()` builds a header dict with a randomized Chrome user-agent profile:

```python
from atskit.http import browser_headers

headers = browser_headers(
    referer="https://jobs.apple.com/en-us/search",
    origin="https://jobs.apple.com",
    accept="application/json, text/plain, */*",
)
```

`BROWSER_HEADER_PROFILES` holds the rotating User-Agent templates. Clients set `Referer`, `Origin`, and `Sec-Fetch-*` fields to match what each ATS expects.

## HTML to Markdown

`html_to_markdown(raw_html)` converts ATS HTML fragments to readable Markdown using `markdownify`, with a BeautifulSoup fallback. Used by clients that return HTML job descriptions (Amazon, Microsoft, Amex, etc.).

## Client-specific pacing

Some clients add extra delays on top of `polite_*`:

- **Workday, Apple, Microsoft, Amex:** pause between paginated requests (`_pause_between_pages`)
- **Greenhouse (discovery):** random 1–3s gap between consecutive Greenhouse `PortalJobsResult` yields in `discover_jobs`

When adding a new client, use `polite_get`/`polite_post` first; add page-level sleeps only if the target API is sensitive to burst traffic.

## Operational guidance

- Keep `max_workers` modest (3–5) for broad discovery runs.
- Do not share one DB across many parallel discovery processes hitting the same hosts.
- Respect each ATS terms of service; ATSKit only uses public job-board endpoints.
