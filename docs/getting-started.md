# Getting started

ATSKit discovers open job listings from public ATS APIs. You supply a SQLite file with company portal metadata; ATSKit queries each portal and streams results back as they complete.

## Install

From GitHub (source):

```bash
pip install git+https://github.com/nirmalhk7/atskit.git
```

From GitHub Packages (built releases — see [Publishing](publishing.md)):

```bash
pip install atskit \
  --index-url https://pypi.pkg.github.com/nirmalhk7/simple/ \
  --extra-index-url https://pypi.org/simple/
```

Requires a GitHub token with `read:packages` when prompted for credentials.

Local development (includes tests and Greenhouse HTML extraction):

```bash
git clone https://github.com/nirmalhk7/atskit.git
cd atskit
pip install -e ".[dev,greenhouse]"
```

Optional extras:

| Extra | Installs | When you need it |
|-------|----------|------------------|
| `greenhouse` | `trafilatura` | Better Greenhouse JD HTML → text conversion |
| `dev` | `pytest`, `responses` | Running the test suite |

## Try it with `example.db`

This repo ships `example.db` at the project root — a SQLite file with **471** real `portal_entries` rows (company name, ATS slug, sample URL, enabled/disabled status). No setup required.

```bash
# CLI
atskit discover --db example.db --max-workers 3

# Python
python -c "
from pathlib import Path
import atskit

for r in atskit.discover_jobs(Path('example.db'), max_workers=3):
    status = 'ERR' if r.error else 'OK'
    print(f'[{status}] {r.entry.name}: {r.job_count} jobs ({r.duration_ms}ms)')
"
```

By default, `discover_jobs` skips portals already scanned today (`last_scanned_date`) and any rows marked disabled (`status = 0`). Pass `skip_scanned_today=False` to rescan everything.

## Minimal workflow

1. **Create or populate a DB** with `portal_entries` (see [Database](database.md)).
2. **Discover jobs** with `discover_jobs(db_path)` or the CLI.
3. **Handle each** `PortalJobsResult` — filter, persist, or display `JobListing` rows.
4. **Fetch a single JD** with `fetch_description(portal, slug, job_id)` when you need full text for one posting.

## Next steps

- [Architecture](architecture.md) — mental model for the library
- [API reference](api.md) — all public functions and models
- [Supported portals](portals.md) — slug formats per ATS
