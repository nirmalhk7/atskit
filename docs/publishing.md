# Publishing

ATSKit is built and published automatically when Python-related files change on `main`.

> **Note:** GitHub does not operate a working PyPI-compatible package registry (`pypi.pkg.github.com` returns 404). Releases are published as **GitHub Release assets** (wheel + sdist), which is the standard way to distribute Python packages on GitHub.

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
4. Writes the new version to `pyproject.toml`, builds, publishes a GitHub Release, then commits and tags `vX.Y.Z` with `[skip publish]`

You do **not** need to bump `pyproject.toml` manually before merging.

### Examples

```text
fix: handle lever 404 gracefully     → patch bump
feat: add icims client                 → minor bump
feat!: rename PortalEntry fields       → major bump
```

## What each publish run does

1. Run `pytest`
2. Compute and write the next semver to `pyproject.toml`
3. Build sdist + wheel (`python -m build`)
4. Commit the version bump and push tag `vX.Y.Z` to `main`
5. Create or update a [GitHub Release](https://github.com/nirmalhk7/atskit/releases) with `dist/*` attached

## Install from a release

Find the latest version on the [releases page](https://github.com/nirmalhk7/atskit/releases), then:

```bash
pip install "https://github.com/nirmalhk7/atskit/releases/download/v0.2.0/atskit-0.2.0-py3-none-any.whl"
```

With optional Greenhouse support, install dependencies first then the wheel:

```bash
pip install trafilatura
pip install "https://github.com/nirmalhk7/atskit/releases/download/v0.2.0/atskit-0.2.0-py3-none-any.whl"
```

Replace `v0.2.0` with the latest tag.

## Install from source

```bash
pip install git+https://github.com/nirmalhk7/atskit.git@v0.2.0
```

## CI vs publish

- [`ci.yml`](../.github/workflows/ci.yml) — tests on every push/PR to `main` (Python 3.11 and 3.12).
- [`publish.yml`](../.github/workflows/publish.yml) — tests, version bump, build, and GitHub Release when Python-related files change on `main`.

## Permissions

The publish workflow uses the built-in `GITHUB_TOKEN` with `contents: write` and `packages: write`. No extra repository secrets are required.
