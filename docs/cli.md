# CLI

ATSKit installs a console script `atskit` when you `pip install` the package.

```bash
atskit --help
```

## `atskit discover`

Stream jobs from every portal in a SQLite database.

```bash
atskit discover --db example.db --max-workers 3
```

| Flag | Env fallback | Description |
|------|--------------|-------------|
| `--db` | `ATSKIT_DB_PATH` | SQLite path with `portal_entries` (required if env unset) |
| `--max-workers` | — | Parallel portal queries (default: `3`) |
| `--include-scanned-today` | — | Rescan portals already marked today |

**Output format** (one line per portal):

```
[ok] Stripe (greenhouse): 42 jobs in 1203ms
[error] SomeCo (lever): 0 jobs in 502ms
  error: HTTP 503
```

Exit code is `0` when the command completes (individual portal errors are printed, not fatal).

### Example session

```bash
export ATSKIT_DB_PATH=example.db
atskit discover --max-workers 5
```

## `atskit list`

List jobs for one portal slug (debugging / spot checks).

```bash
atskit list --portal greenhouse --slug stripe
```

Prints up to 20 jobs with title and location:

```
greenhouse/stripe: 87 jobs
  - Software Engineer | San Francisco
  - ...
```

## Tips

- Use `example.db` in the repo root for a quick smoke test.
- For automation, prefer the Python API (`discover_jobs`) — it returns structured `PortalJobsResult` objects instead of printed lines.
- Set `ATSKIT_DB_PATH` in your shell profile if you always query the same database.
