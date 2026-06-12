#!/usr/bin/env python3
"""Compute next semver from git history and update pyproject.toml.

Used by the Publish GitHub Actions workflow on each qualifying push to main.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = re.compile(r'^version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', re.M)
TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


def parse_version(raw: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"\d+\.\d+\.\d+", raw.strip().lstrip("v"))
    if not match:
        raise ValueError(f"invalid semver: {raw!r}")
    major, minor, patch = raw.strip().lstrip("v").split(".")
    return int(major), int(minor), int(patch)


def format_version(parts: tuple[int, int, int]) -> str:
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def version_gt(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return a > b


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def read_pyproject_version(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        raise ValueError(f"could not find version in {path}")
    return parse_version(match.group("version"))


def write_pyproject_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise ValueError(f"could not update version in {path}")
    path.write_text(updated, encoding="utf-8")


def latest_tag_version() -> tuple[int, int, int] | None:
    try:
        tag = run_git("describe", "--tags", "--abbrev=0", "--match", "v*")
    except subprocess.CalledProcessError:
        return None
    match = TAG_RE.fullmatch(tag)
    if not match:
        return None
    return parse_version(match.group("version"))


def commit_messages_since_tag(tag_version: tuple[int, int, int] | None) -> list[str]:
    if tag_version is None:
        log_range = "HEAD"
    else:
        log_range = f"v{format_version(tag_version)}..HEAD"
    try:
        raw = run_git("log", log_range, "--pretty=%B")
    except subprocess.CalledProcessError:
        return []
    if not raw:
        return []
    return [block.strip() for block in raw.split("\n\n") if block.strip()]


def classify_bump(messages: list[str]) -> str:
    for message in messages:
        first_line = message.splitlines()[0].strip()
        if re.search(r"BREAKING CHANGE", message, re.IGNORECASE):
            return "major"
        if re.match(r"^[a-z]+!(\(|:)", first_line, re.IGNORECASE):
            return "major"
    for message in messages:
        first_line = message.splitlines()[0].strip()
        if re.match(r"^feat(\(|:)", first_line, re.IGNORECASE):
            return "minor"
    return "patch"


def bump(version: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if level == "major":
        return major + 1, 0, 0
    if level == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def max_version(
    a: tuple[int, int, int] | None,
    b: tuple[int, int, int] | None,
) -> tuple[int, int, int]:
    if a is None:
        return b or (0, 0, 0)
    if b is None:
        return a
    return a if version_gt(a, b) else b


def compute_next_version(pyproject: Path) -> tuple[str, str]:
    file_version = read_pyproject_version(pyproject)
    tag_version = latest_tag_version()
    base = max_version(file_version, tag_version)
    messages = commit_messages_since_tag(tag_version)
    if not messages and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        messages = [os.environ.get("GITHUB_COMMIT_MESSAGE", "chore: manual publish")]
    if not messages:
        messages = ["chore: publish"]
    level = classify_bump(messages)
    next_version = format_version(bump(base, level))
    return next_version, level


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the computed version into pyproject.toml",
    )
    args = parser.parse_args()

    next_version, level = compute_next_version(args.pyproject)
    if args.write:
        write_pyproject_version(args.pyproject, next_version)

    print(next_version)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"version={next_version}\n")
            handle.write(f"bump={level}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
