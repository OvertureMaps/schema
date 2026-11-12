#!/usr/bin/env bash
# Rebase the current branch onto <onto>, regenerating uv.lock where it conflicts.
#
#     .github/scripts/rebase-regenerating-lock.sh <onto>
#
# uv.lock is generated, so a textual conflict in it has no meaning to resolve by
# hand: `main` and `vnext` lock different Python ranges, and every
# `uv lock --upgrade` on main rewrites hunks that vnext's lock also touches. When
# uv.lock is the only conflicted file, take the <onto> side and run `uv lock` against
# the pyproject.toml files already checked out: uv keeps the pinned versions and
# drops or adds only what the branch's constraints change.
#
# Regenerating runs uv's resolver over the branch's pyproject.toml files, so it is
# off unless REGENERATE_LOCK=true. A caller sets that only for branches whose
# content it trusts (not a fork PR).
#
# On failure the rebase is left in progress, so the caller can read the conflicted
# files and run `git rebase --abort`.

set -uo pipefail

main() {
  local onto=${1:?usage: rebase-regenerating-lock.sh <onto>}

  git rebase "$onto" && return 0

  # Each pass resolves one commit; a later commit may conflict in uv.lock again.
  while true; do
    local conflicts
    conflicts=$(git diff --name-only --diff-filter=U)
    [ "$conflicts" = "uv.lock" ] || return 1
    [ "${REGENERATE_LOCK:-}" = "true" ] || return 1

    git checkout --ours uv.lock || return 1
    uv lock || return 1
    git add uv.lock || return 1
    GIT_EDITOR=true git rebase --continue && return 0
  done
}

main "$@"; exit $?
