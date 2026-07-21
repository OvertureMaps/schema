# Contributing to Overture Schema

Thank you for your interest in contributing.

> **The branching and versioning strategy is rolling out in phases.** See the
> [DevOps tracking issue #490](https://github.com/OvertureMaps/schema/issues/490)
> for current status and what is planned next.

## Where to send your change

This repository uses a two-branch model. Target the branch that matches your
change; when in doubt, target `main` and note in your PR if you think it belongs
in `vnext`. The
[Change Classification](https://lf-overturemaps.atlassian.net/wiki/spaces/SCHEM/pages/14286874/Schema+versioning+and+stability#Change-Classification)
wiki page breaks down what counts as a minor vs. major change.

| Branch | Use for |
|--------|---------|
| `main` | Default branch. Bug fixes, minor features, schema improvements. |
| `vnext` | Major or breaking changes tied to an active `vnext` milestone. |

Three common paths take a branch to a merge. Expand each for the commit-level flow.

<details>
<summary><strong><code>main</code> &rarr; patch (no version bump)</strong></summary>

Everyday bug fixes and schema tweaks. You do not touch the version; CI computes
the patch at publish time and no GitHub Release is cut.

```mermaid
gitGraph
   commit id: "overture-schema-v1.17.0"
   branch fix-places-brand-enum
   checkout fix-places-brand-enum
   commit id: "fix brand enum values"
   commit id: "add bugfix fragment"
   checkout main
   merge fix-places-brand-enum id: "PR #561"
   commit id: "more fixes"
```

</details>

<details>
<summary><strong><code>main</code> &rarr; minor release (version bump)</strong></summary>

A minor feature that bumps `major.minor` in the PR and builds the changelog. On
merge, `release-trigger` cuts the release.

```mermaid
gitGraph
   commit id: "overture-schema-v1.17.0"
   branch feat-base-land-cover
   checkout feat-base-land-cover
   commit id: "add land_cover subtype"
   commit id: "bump 1.17 to 1.18 + build changelog"
   checkout main
   merge feat-base-land-cover id: "PR #564" tag: "overture-schema-v1.18.0"
   commit id: "next work"
```

</details>

<details>
<summary><strong><code>vnext</code> &rarr; major release</strong></summary>

Breaking changes stack on `vnext` until the milestone is ready. Then `vnext`
merges into `main` as a regular merge (not a squash), which cuts the release.

```mermaid
gitGraph
   commit id: "overture-schema-v1.18.0"
   branch vnext
   checkout vnext
   branch feat-transportation-access
   checkout feat-transportation-access
   commit id: "breaking: restructure access"
   commit id: "add breaking fragment"
   checkout vnext
   merge feat-transportation-access id: "PR #570"
   branch feat-divisions-hierarchy
   checkout feat-divisions-hierarchy
   commit id: "breaking: new division hierarchy"
   commit id: "add breaking fragment"
   checkout vnext
   merge feat-divisions-hierarchy id: "PR #572"
   commit id: "bump 1.18 to 2.0 + build changelog"
   checkout main
   merge vnext id: "release merge (not squash)" tag: "overture-schema-v2.0.0"
   commit id: "next patch work"
```

</details>

The `bump ... + build changelog` commit edits the package version in
`pyproject.toml` and folds its `changelog.d/` fragments into `CHANGELOG.md`. On
merge to `main`, CI cuts a published GitHub Release tagged
`<package>-v<major>.<minor>.0` with those notes. See
[docs/versioning.md](docs/versioning.md).

## Opening a PR

A couple of CI checks comment on your PR when they need something. Each explains
itself inline, so follow the comment it leaves rather than a copy here:

- [vnext compatibility check](.github/workflows/vnext-compat.yaml): fails and
  posts the fix if your change clashes with unreleased `vnext` work.
- [PR advisory check](.github/workflows/pr-advisory.yaml): nudges you on a likely
  change-type / target-branch mismatch. Advisory only; the reviewer decides.

If you have an open PR against `vnext`, its base may be force-updated after a
merge to `main`; run `git pull --rebase` before pushing again.

## Changing a package version

- `<major>.<minor>` is your call: edit it in `pyproject.toml` and reset patch to
  `0` (e.g. `1.17.1` becomes `1.18.0`). Minor bumps target `main`; major bumps
  target `vnext`.
- `<patch>` is computed by CI at publish time; never edit it manually.
- Every package versions and releases independently. Consumers pin only
  `overture-schema`, which pulls in the theme and support packages for a coherent
  set.
- A `major.minor` bump **requires a changelog fragment**. Add one under
  `packages/<package>/changelog.d/` and run
  `uvx towncrier build --config pyproject.toml --dir packages/<package>`. CI
  enforces it.

Full version scheme, tag scheme, and release flow: [docs/versioning.md](docs/versioning.md).
