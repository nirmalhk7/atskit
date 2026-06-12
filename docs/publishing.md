# Publishing

ATSKit is built and published to **GitHub Packages** automatically when Python-related files change on `main`.

## Workflow

File: [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)

| Trigger | When it runs |
|---------|----------------|
| `push` to `main` | Any commit touching `**/*.py`, `pyproject.toml`, or `requirements.txt` |
| `workflow_dispatch` | Manual run from the Actions tab |

Commits with `[skip publish]` in the message are ignored (used by the release bot commit).

## Automatic versioning

Version bumps are computed by [`scripts/bump_version.py`](../scripts/bump_version.py) using [Semantic Versioning](https://semver.org/):

| Commit message pattern | Bump |
|------------------------|------|
| `BREAKING CHANGE` or `type!:` / `type!(` | **major** (`1.2.3` → `2.0.0`) |
| `feat:` or `feat(` | **minor** (`1.2.3` → `1.3.0`) |
| anything else | **patch** (`1.2.3` → `1.2.4`) |

The script:

1. Reads the current version from `pyproject.toml` and the latest `v*` git tag
2. Uses the higher of the two as the base
3. Inspects commit messages since the last tag
4. Writes the new version to `pyproject.toml`, builds, publishes, then commits and tags `vX.Y.Z` with `[skip publish]`

You do **not** need to bump `pyproject.toml` manually before merging.

### Examples

```text
fix: handle lever 404 gracefully     → patch bump
feat: add icims client                 → minor bump
feat!: rename PortalEntry fields       → major bump
```

## What each publish run does

1. Run `pytest`
2. Compute and write the next semver
3. Build sdist + wheel (`python -m build`)
4. Upload to `https://upload.pypi.pkg.github.com/nirmalhk7/`
5. Commit the version bump, tag `vX.Y.Z`, push to `main`

## Install from GitHub Packages

Published package page: [github.com/nirmalhk7/atskit/packages](https://github.com/nirmalhk7/atskit/packages)

GitHub Packages requires authentication for `pip install` in most cases. Create a [personal access token](https://github.com/settings/tokens) with `read:packages`.

```bash
pip install atskit \
  --index-url https://pypi.pkg.github.com/nirmalhk7/simple/ \
  --extra-index-url https://pypi.org/simple/
```

When prompted for credentials, use your GitHub username and the token as the password. Alternatively, configure `~/.netrc`:

```
machine pypi.pkg.github.com
login nirmalhk7
password YOUR_GITHUB_TOKEN
```

Optional extras:

```bash
pip install "atskit[greenhouse]" \
  --index-url https://pypi.pkg.github.com/nirmalhk7/simple/ \
  --extra-index-url https://pypi.org/simple/
```

## CI vs publish

- [`ci.yml`](../.github/workflows/ci.yml) — tests on every push/PR to `main` (Python 3.11 and 3.12).
- [`publish.yml`](../.github/workflows/publish.yml) — tests, version bump, build, and upload when Python-related files change on `main`.

## Permissions

The publish workflow uses the built-in `GITHUB_TOKEN` with `contents: write` and `packages: write`. No extra repository secrets are required.
