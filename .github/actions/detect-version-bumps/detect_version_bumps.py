#!/usr/bin/env python3

"""
Detect per-package version bumps between two commits on main.

Run from the repository root:

    python3 detect_version_bumps.py <before-commit>

Compares each `packages/*/pyproject.toml` at the working tree against its
content at the `before` commit, and records the packages whose
`<major>.<minor>.<patch>` increased. All three components are human-owned
(see docs/versioning.md); any increase, including patch-only, cuts a release.

Requires the shared `package_versions` module on PYTHONPATH (it lives in
`.github/workflows/scripts/`); the `detect-version-bumps` action wires this
up.

Output (stdout, `$GITHUB_OUTPUT` format; progress goes to stderr):
    count=<n>      Number of bumped packages.
    bumps=<json>   JSON array of {"package", "version", "tag"} objects, one per
                   bump. Consumed as a matrix by the release job.

Exit status:
    0  Success (including the no-bump case).
    1  Usage error, a package's version went backwards, or a major bump does
       not cascade to its dependents; none of these must ever land on main.
"""

from pathlib import Path
import json
import re
import subprocess
import sys
import tomllib

from package_versions import check_major_cascade, package_manifests

# Released versions are plain X.Y.Z by policy (docs/versioning.md); PEP 440
# variants like 1.2.3rc4 or 1.2.3.post1 must not appear in pyproject.toml.
PLAIN_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def semver(pyproject_blob: bytes) -> tuple[int, int, int]:
    """Parse `project.version` from pyproject.toml bytes into (major, minor, patch)."""
    version = str(tomllib.loads(pyproject_blob.decode("utf-8"))["project"]["version"])
    match = PLAIN_SEMVER.match(version)
    if not match:
        raise ValueError(
            f"version {version!r} is not plain <major>.<minor>.<patch>; "
            "pre-release/post-release segments are not allowed in pyproject.toml "
            "(see docs/versioning.md)"
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def git_show(commit: str, path: str) -> bytes | None:
    """
    Return the bytes of `path` at `commit`, or None if unreadable.

    A blob can be unreadable after a force-push, a history rewrite, or for a
    brand-new file. Treat that as "no previous version" rather than failing
    every subsequent push.
    """
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def info(message: str) -> None:
    print(message, file=sys.stderr)


def main(before_commit: str) -> None:
    bumps: list[dict[str, str]] = []
    errors: list[str] = []

    for path in sorted(Path("packages").glob("*/pyproject.toml")):
        package = path.parent.name
        pyproject = path.as_posix()  # git wants forward slashes on every OS

        after = semver(path.read_bytes())

        before_blob = git_show(before_commit, pyproject)
        if before_blob is None:
            info(f"No readable {pyproject} at {before_commit}, skipping {package}.")
            continue
        before = semver(before_blob)

        if after == before:
            continue

        before_str = ".".join(map(str, before))
        after_str = ".".join(map(str, after))

        if after < before:
            errors.append(f"{package}: {before_str} -> {after_str}")
            continue

        info(f"{package}: {before_str} -> {after_str} (bump)")
        bumps.append({"package": package, "version": after_str, "tag": f"{package}-v{after_str}"})

    if errors:
        for e in errors:
            info(
                f"::error::{e}: version went backwards. Version decreases "
                "must never land on main; revert or fix the version."
            )
        sys.exit(1)

    # Belt-and-braces re-check of the major-bump cascade (primary enforcement
    # is the PR-time version check). Publishing releases with a non-cascaded
    # major bump would poison dependents' declared floors.
    after_manifests = {
        path.parent.name: tomllib.loads(path.read_text(encoding="utf-8"))
        for path in sorted(Path("packages").glob("*/pyproject.toml"))
    }
    violations = check_major_cascade(package_manifests(before_commit), after_manifests)
    if violations:
        for v in violations:
            info(f"::error::{v}")
        sys.exit(1)

    if not bumps:
        info("No version bumps detected.")

    print(f"count={len(bumps)}")
    print(f"bumps={json.dumps(bumps)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} BEFORE_COMMIT", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
