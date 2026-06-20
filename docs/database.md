# Database

ATSKit uses a single SQLite table: `portal_entries`. Everything else in your `.db` file is ignored.

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `name` | `TEXT PRIMARY KEY` | Display company name (e.g. `Stripe`) |
| `slug` | `TEXT NOT NULL` | ATS-specific board identifier (see [Supported portals](portals.md)) |
| `portal` | `TEXT NOT NULL` | Portal key: `greenhouse`, `lever`, `workday`, … |
| `sample_url` | `TEXT NOT NULL` | Example job or board URL used when the row was created |
| `updated_on` | `TEXT NOT NULL` | ISO date (`YYYY-MM-DD`) when the row was last written |
| `last_scanned_date` | `TEXT NOT NULL` | ISO date of last successful `discover_jobs` scan; empty if never scanned |
| `status` | `INTEGER NOT NULL DEFAULT 1` | `1` = enabled, `0` = disabled; disabled portals are skipped by `discover_jobs` |

The table is created automatically on first `PortalStore` access. Older databases without `last_scanned_date` or `status` are migrated with `ALTER TABLE`.

## `PortalStore`

```python
from atskit import PortalStore, PortalEntry

store = PortalStore("portals.db")

store.replace([
    PortalEntry(
        name="Stripe",
        slug="stripe",
        portal="greenhouse",
        sample_url="https://boards.greenhouse.io/stripe/jobs/123",
    ),
])

entries = store.load()
store.mark_scanned_today("Stripe")
store.close()
```

### `replace(entries)`

Replaces the entire `portal_entries` table. Rows with unsupported `portal` values or empty `name`/`slug` are skipped. `status` is written from the supplied `PortalEntry` objects, and `last_scanned_date` is preserved by company name when possible.

### `load()`

Returns all entries ordered by lowercased name.

### `mark_scanned_today(name)`

Sets `last_scanned_date` to today. Called automatically by `discover_jobs` after a successful portal query (when `mark_scanned=True`).

## `example.db`

The repo includes `example.db` with 471 portals copied from a real discovery corpus. Use it to try ATSKit without building your own list:

```bash
cp example.db my-portals.db
atskit discover --db my-portals.db
```

## Building portals from applied jobs

If you have a list of jobs you've already applied to (or scraped elsewhere), `build_portals` and `sync_portals_from_applied` infer portal rows by classifying each job URL:

```python
import atskit

def my_applied_jobs():
  return [
      {"company_name": "Acme", "job_link": "https://jobs.lever.co/acme/abc-123"},
      # ...
  ]

entries = atskit.build_portals("portals.db", applied_jobs=my_applied_jobs)
added = atskit.sync_portals_from_applied("portals.db", applied_jobs=my_applied_jobs)
```

**Applied job dict keys** (flexible aliases):

| Field | Accepted keys |
|-------|----------------|
| URL | `job_link`, `jobLink`, `url` |
| Company | `company_name`, `company`, `Company` |

Company names are canonicalized (`title` case) and fuzzy-merged at ≥90% similarity (`rapidfuzz`). Built-in enterprise boards (Apple, Amazon, Microsoft, American Express) are always injected.

`build_portals` skips rebuilding if the DB already has non-builtin entries unless `force_refresh=True`.
When a company name already exists, its current `status` flag is kept so manually disabled rows stay disabled after refreshes.

## What ATSKit does not store

- Discovered job listings
- Job descriptions after fetch
- Scan errors or API telemetry

Consumers persist those in their own tables or files.
