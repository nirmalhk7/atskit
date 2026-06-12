# Supported portals

ATSKit registers nine ATS backends. Each client module lives under `atskit/ats/` and is keyed by the `portal` column in `portal_entries`.

## Summary

| Portal key | Host examples | `slug` format |
|------------|---------------|---------------|
| `greenhouse` | `boards.greenhouse.io`, `*.greenhouse.io` | Company board token (e.g. `stripe`) |
| `lever` | `jobs.lever.co`, `jobs.eu.lever.co` | Company token (e.g. `netflix`) |
| `ashby` | `jobs.ashbyhq.com` | Company token |
| `gem` | `jobs.gem.com` | Company token |
| `workday` | `*.wd*.myworkdayjobs.com` | `host\|tenant\|site` (see below) |
| `apple` | `jobs.apple.com` | Always `apple` |
| `amazon` | `amazon.jobs` | Always `amazon` |
| `microsoft` | `apply.careers.microsoft.com` | Always `microsoft` |
| `american_express` | `careers.americanexpress.com` | Always `american_express` |

## Per-portal notes

### Greenhouse

- **List API:** `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
- **Slug:** board token from URL (`boards.greenhouse.io/stripe/...` → `stripe`)
- **Optional dep:** install `atskit[greenhouse]` for `trafilatura`-based HTML cleanup

### Lever

- **Slug:** first path segment (`jobs.lever.co/acme/...` → `acme`)

### Ashby / Gem

- **Slug:** first path segment; job id is second segment when present

### Workday

Workday uses a composite slug:

```
{host}|{tenant}|{site}
```

Example:

```
example.wd1.myworkdayjobs.com|example|External
```

Parsed from CXS URLs (`/wday/cxs/{tenant}/{site}/...`) or public locale paths (`/en-US/{site}/job/...`). The client paginates via POST to the CXS jobs endpoint.

### Apple, Amazon, Microsoft, American Express

These use a fixed slug matching the portal key (`apple`, `amazon`, …). Clients apply company-specific search filters (US software-engineer style queries) rather than listing an arbitrary third-party board.

Built-in `PortalEntry` rows for all four are auto-injected by `load_portals` / `build_portals`.

## URL classification

`classify_url(url)` returns a `PortalClassification` or `None`:

```python
import atskit

c = atskit.classify_url("https://jobs.lever.co/acme/abc-123")
# PortalClassification(portal='lever', slug='acme', job_id='abc-123')
```

Supported URL shapes include:

- Greenhouse job and board URLs (including custom `*.greenhouse.io` hosts)
- Lever, Ashby, Gem job URLs
- Workday public and CXS paths
- Apple `/en-us/details/{id}/...`
- Amazon public and account apply URLs
- Microsoft careers apply and jobs hosts
- American Express careers and Oracle CX redirect URLs

Unsupported URLs return `None` — `build_portals` counts these as skipped.

## Listing a single board

```python
import atskit

jobs = atskit.list_jobs("greenhouse", "stripe")
desc = atskit.fetch_description("greenhouse", "stripe", "123456")
```

Use `atskit list --portal greenhouse --slug stripe` from the CLI for a quick check.
