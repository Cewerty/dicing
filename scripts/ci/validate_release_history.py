"""
Guard for the release workflow: the latest ``vX.Y.Z`` tag must be part of the current history.

python-semantic-release computes the next version from the latest tag reachable from ``HEAD``.
If history was rewritten and the tagged commit "got lost", or if there are no tags at all,
it would silently compute a wrong (possibly lower) version. This script stops the release
with a clear message instead.

Usage: ``python scripts/ci/validate_release_history.py [--repo PATH]``. Exit code 0 — ok, 1 — problem.
Depends only on ``git`` and the standard library.
"""

from __future__ import annotations

import argparse
import re
import subprocess  # noqa: S404 — the script's whole job is to call git
import sys
from pathlib import Path

VERSION_TAG = re.compile(r"^v\d+\.\d+\.\d+$")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)  # noqa: S603, S607


def latest_version_tag(repo: Path) -> str | None:
    """Return the highest ``vX.Y.Z`` tag of the repository, or None if there are no such tags."""
    result = _git(repo, "tag", "--list", "v*", "--sort=-v:refname")
    if result.returncode != 0:
        raise RuntimeError(f"git tag failed: {result.stderr.strip()}")
    return next((tag for tag in result.stdout.split() if VERSION_TAG.match(tag)), None)


def validate(repo: Path) -> str | None:
    """Return an error message, or None if the release history is consistent."""
    tag = latest_version_tag(repo)
    if tag is None:
        return (
            "no vX.Y.Z tags found. Create the baseline tag of the last manual release first, "
            "e.g. `git tag -a v0.3.3 <commit> -m v0.3.3 && git push origin v0.3.3`, "
            "otherwise semantic-release would start counting from 0.0.0."
        )
    if _git(repo, "merge-base", "--is-ancestor", tag, "HEAD").returncode != 0:
        return (
            f"latest tag {tag} is not an ancestor of HEAD — history was probably rewritten "
            "after the release. Restore the tagged commit in main or move the tag before releasing."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    """Run the check and print the result."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="path to the git repository")
    args = parser.parse_args(argv)
    error = validate(args.repo)
    if error is not None:
        print(f"release history check failed: {error}", file=sys.stderr)
        return 1
    print(f"release history ok: {latest_version_tag(args.repo)} is in the history of HEAD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
