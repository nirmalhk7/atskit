# ATSKit

ATSKit is a standalone Python library for discovering jobs across supported applicant tracking systems (ATS). It reads company portal metadata from a caller-supplied SQLite database, queries each portal's public API, and **streams results per portal** as each query completes.

**Documentation:** [docs/](docs/README.md) — getting started, API reference, portal guide, and more.

## Install

From GitHub:

```bash
pip install git+https://github.com/nirmalhk7/atskit.git
```

Built wheels are published to [GitHub Releases](https://github.com/nirmalhk7/atskit/releases) automatically on every `main` commit that touches Python files. Versioning is semver and fully automatic — see [docs/publishing.md](docs/publishing.md).

For local development:

```bash
git clone https://github.com/nirmalhk7/atskit.git
cd atskit
pip install -e ".[dev,greenhouse]"
```

Optional Greenhouse HTML extraction:

```bash
pip install "atskit[greenhouse]"
```

## Database contract

Pass any SQLite file path. ATSKit reads/writes only the `portal_entries` table.

An `example.db` ships with this repo (471 sample portals copied from a real discovery run). Try:

```bash
atskit discover --db example.db --max-workers 3
```

| Column | Type |
|--------|------|
| `name` | TEXT PRIMARY KEY |
| `slug` | TEXT |
| `portal` | TEXT |
| `sample_url` | TEXT |
| `updated_on` | TEXT |
| `last_scanned_date` | TEXT |

The table is created automatically if missing.

## Discover jobs (streaming)

```python
from pathlib import Path
import atskit

for result in atskit.discover_jobs(Path("portals.db")):
    print(result.entry.name, result.job_count, result.error)
    for job in result.jobs:
        print(" ", job.title, job.apply_url)
```

Each yield is a `PortalJobsResult` with:

- `entry` — `PortalEntry` from the DB
- `jobs` — list of `JobListing`
- `error` — error string if the portal query failed
- `duration_ms` — query duration
- `job_count` — computed property

## Lower-level API

```python
import atskit

# URL classification
cls = atskit.classify_url("https://boards.greenhouse.io/stripe/jobs/123")

# Single portal
jobs = atskit.list_jobs("greenhouse", "stripe")
desc = atskit.fetch_description("greenhouse", "stripe", "123")

# Portal store
store = atskit.PortalStore("portals.db")
entries = atskit.load_portals("portals.db")
```

## Supported ATS platforms

| Portal key | Examples |
|------------|----------|
| `greenhouse` | boards.greenhouse.io |
| `lever` | jobs.lever.co |
| `ashby` | jobs.ashbyhq.com |
| `gem` | jobs.gem.com |
| `workday` | *.myworkdayjobs.com |
| `apple` | jobs.apple.com |
| `amazon` | amazon.jobs |
| `microsoft` | apply.careers.microsoft.com |
| `american_express` | careers.americanexpress.com |

## CLI

```bash
export ATSKIT_DB_PATH=portals.db
atskit discover --max-workers 3
atskit list --portal greenhouse --slug stripe
```

## Development

```bash
pip install -e ".[dev,greenhouse]"
pytest -q
```

## Used by VOYAGER

[VOYAGER](https://github.com/nirmalhk7/VOYAGER) consumes ATSKit as a git submodule for Phase 1 job discovery. Portal population from applied jobs uses `atskit.build_portals(db, applied_jobs=provider)`.
