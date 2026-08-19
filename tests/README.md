# Workspace tests

Checks whose subject is the repository or the workspace as a whole, and which
therefore cannot correctly live in any one package.

A test belongs here only if both hold:

- **Its subject spans packages, or sits outside them.** `test_documented_imports`
  reads every tracked Markdown file, including root-level ones that ship in no
  package, and imports across every package's namespace — `overture.schema.codegen`
  among them, which no single distribution depends on.
- **It cannot run from one package's install.** Placing such a test under
  `packages/<pkg>/tests/` would make that package's suite depend on packages its
  `pyproject.toml` does not declare, and it would pass only because the workspace
  happens to install everything.

Anything that can be scoped to a package belongs in that package's `tests/`
instead. This directory is not a home for tests that are merely inconvenient to
place.

`make check` covers this tree the same way it covers `packages/` — ruff, `ruff
format`, mypy, and pytest. Note that a bare `pytest packages/` does not; use
`make test` or include `tests/` explicitly.
