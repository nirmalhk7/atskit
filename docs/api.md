# API reference

All symbols below are importable from the top-level `atskit` package unless noted.

## Discovery

### `discover_jobs(db_path, *, skip_scanned_today=True, max_workers=3, portals=None, mark_scanned=True)`

```python
from pathlib import Path
import atskit

for result in atskit.discover_jobs(Path("portals.db")):
    ...
```

**Yields:** `PortalJobsResult` — one per portal, in completion order (not input order).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `db_path` | — | SQLite file with `portal_entries` |
| `skip_scanned_today` | `True` | Skip rows where `last_scanned_date` is today |
| `max_workers` | `3` | Thread pool size (capped at portal count) |
| `portals` | `None` | If set, only query these portal keys (e.g. `["greenhouse", "lever"]`) |
| `mark_scanned` | `True` | Update `last_scanned_date` on success |

Rows with `status = 0` are ignored before any work is submitted to the thread pool.

**Greenhouse pacing:** consecutive Greenhouse results get a random 1–3s delay before yield to reduce burst traffic.

## Job queries

### `list_jobs(portal, slug) -> list[JobListing]`

Query one board directly. Returns `[]` for unknown portals or client failures.

### `list_jobs_for_entry(entry: PortalEntry) -> list[JobListing]`

Same as `list_jobs(entry.portal, entry.slug)`.

### `fetch_description(portal, slug, job_id) -> FetchDescriptionResult`

Fetch full JD text for one posting. Returns structured result with `description_md` or `error`.

### `fetch_description_for_url(url) -> FetchDescriptionResult | None`

Classifies `url`, extracts job id, then calls `fetch_description`. Returns `None` if URL is unsupported.

## Portal management

### `load_portals(db_path) -> list[PortalEntry]`

Load supported entries, ensure builtins exist, shuffle order.

### `build_portals(db_path, *, applied_jobs=None, force_refresh=False) -> list[PortalEntry]`

Rebuild portal table from applied jobs and/or builtins. See [Database](database.md).

### `sync_portals_from_applied(db_path, applied_jobs) -> int`

Add new companies from applied jobs without full rebuild. Returns count of new entries.

### `PortalStore(db_path)`

Low-level SQLite access. See [Database](database.md).

## URL utilities

### `classify_url(url) -> PortalClassification | None`

Parse a job URL into `portal`, `slug`, and `job_id`.

### `clean_url(url, preserve_query_domains=None) -> str`

Strip query string unless host is in the allowlist set.

### `URLUtility`

Class wrapper exposing the same helpers and portal constants for legacy call sites.

## Registry

### `CLIENTS`

`dict[str, module]` — portal key to client module.

### `SUPPORTED_PORTALS`

`frozenset` of registered portal keys.

### `get_client(portal) -> module | None`

Lookup client module by portal key.

## Models

### `JobListing`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | ATS-native job identifier |
| `title` | `str` | Posting title |
| `location` | `str` | Human-readable location |
| `description_md` | `str` | Description as Markdown (may be empty in list responses) |
| `apply_url` | `str` | Canonical apply URL |
| `raw` | `dict` | Original API payload fragments |

### `PortalEntry` (frozen)

`name`, `slug`, `portal`, `sample_url`, `last_scanned_date`, `status`.

### `PortalJobsResult`

| Field | Type | Description |
|-------|------|-------------|
| `entry` | `PortalEntry` | Portal that was queried |
| `jobs` | `list[JobListing]` | Results (empty on error) |
| `error` | `str \| None` | Error message if query failed |
| `duration_ms` | `int` | Wall time for this portal |
| `scanned_at` | `datetime` | UTC timestamp |
| `job_count` | `int` | Computed: `len(jobs)` |

### `PortalClassification`

`portal`, `slug`, `job_id` — from `classify_url`.

### `FetchDescriptionResult`

`portal`, `slug`, `job_id`, `description_md`, `error`.
