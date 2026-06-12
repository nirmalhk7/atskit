# Adding an ATS client

This guide walks through implementing a new portal backend and wiring it into ATSKit.

## 1. Create the client module

Add `atskit/ats/your_ats.py`:

```python
"""Your ATS public API."""

from __future__ import annotations

from .base import JobModel, polite_get, html_to_markdown


def list_jobs(slug: str) -> list[JobModel]:
    url = f"https://api.example.com/{slug}/jobs"
    resp = polite_get(url)
    if resp.status_code != 200:
        return []
    out: list[JobModel] = []
    for item in resp.json().get("jobs", []):
        out.append(
            JobModel(
                id=str(item["id"]),
                title=item.get("title", ""),
                location=item.get("location", ""),
                description_md=html_to_markdown(item.get("description_html", "")),
                apply_url=item.get("url", ""),
                raw=item,
            )
        )
    return out


def fetch_description(slug: str, job_id: str) -> str:
    resp = polite_get(f"https://api.example.com/{slug}/jobs/{job_id}")
    if resp.status_code != 200:
        return ""
    return html_to_markdown(resp.json().get("description_html", ""))
```

**Contract:**

- `list_jobs(slug) -> list[JobListing]` — required
- `fetch_description(slug, job_id) -> str` — optional but recommended
- Use `polite_get` / `polite_post` from `.base` (re-exported from `http.py`)
- Return `[]` or `""` on failure; log briefly if helpful
- Map API payloads to `JobModel` with `raw` preserved for debugging

## 2. Register in `atskit/ats/__init__.py`

```python
from . import your_ats

CLIENTS = {
    # ...
    "your_ats": your_ats,
}
```

## 3. Add URL classification

In `atskit/url.py`:

1. Define a constant: `YOUR_ATS = "your_ats"`
2. Add it to `SUPPORTED_PORTALS`
3. Add host regex and parsing logic inside `classify_url()`
4. Export the constant from `URLUtility` if needed

`classify_url` must return `PortalClassification(portal, slug, job_id)` for job URLs your users will pass to `build_portals` or `fetch_description_for_url`.

## 4. Portal map builtins (if applicable)

If the ATS is a single fixed board (like Apple/Amazon), add a `PortalEntry` to `_BUILTIN_ENTRIES` in `portal_map.py` and include the portal in `_FIXED_PORTALS` if it should survive rebuilds.

## 5. Tests

Add `tests/test_your_ats.py` with mocked `polite_get`/`polite_post` responses:

```python
from unittest.mock import MagicMock, patch
from atskit.ats import your_ats


@patch("atskit.ats.your_ats.polite_get")
def test_list_jobs_maps_payload(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"jobs": [...]})
    jobs = your_ats.list_jobs("acme")
    assert len(jobs) == 1
```

Run `pytest -q` from the repo root.

## 6. Documentation

Update:

- [Supported portals](portals.md) — host patterns and slug format
- [README](../README.md) — summary table if user-facing

## Checklist

- [ ] `list_jobs` returns `JobListing` with stable `id` and `apply_url`
- [ ] `fetch_description` returns Markdown text
- [ ] Registered in `CLIENTS`
- [ ] `classify_url` handles job URLs
- [ ] Uses `polite_get`/`polite_post`
- [ ] Unit tests with mocked HTTP
- [ ] Docs updated

## Slug design tips

- **Simple token** (Greenhouse/Lever style): store the board/company id from the URL path.
- **Composite** (Workday style): encode multiple identifiers in one string with a delimiter documented in [portals.md](portals.md).
- **Fixed** (enterprise boards): use the portal key as slug when there is only one global board.

Consumers store whatever slug your client expects in `portal_entries.slug` — keep it derivable from a sample job URL whenever possible.
