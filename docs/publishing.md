# Publishing

ATSKit is built and published to **GitHub Packages** (Python registry) via GitHub Actions.

## Workflow

File: [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)

| Trigger | When it runs |
|---------|----------------|
| `push` tags matching `v*` | e.g. `git tag v0.1.0 && git push origin v0.1.0` |
| `release` `published` | Creating a GitHub Release |
| `workflow_dispatch` | Manual run from the Actions tab |

Steps on each run:

1. Install Python 3.12
2. Run the test suite (`pytest`)
3. Build sdist + wheel (`python -m build`)
4. Upload to `https://upload.pypi.pkg.github.com/nirmalhk7/`

## Release checklist

1. Bump `version` in [`pyproject.toml`](../pyproject.toml).
2. Commit and push to `main`.
3. Tag and push:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
   Or create a GitHub Release from the tag (also triggers publish).

Each version is published once; re-publishing the same version will fail.

## Install from GitHub Packages

Published package page: [github.com/nirmalhk7/atskit/packages](https://github.com/nirmalhk7/atskit/packages)

GitHub Packages requires authentication for `pip install` in most cases. Create a [personal access token](https://github.com/settings/tokens) with `read:packages`.

```bash
export GITHUB_TOKEN=ghp_...
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
- [`publish.yml`](../.github/workflows/publish.yml) — tests again, then builds and uploads on release tags.

## Permissions

The publish workflow uses the built-in `GITHUB_TOKEN` with `packages: write`. No extra repository secrets are required for publishing from this repo.
