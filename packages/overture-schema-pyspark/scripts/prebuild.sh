#!/usr/bin/env bash
# Regenerates the PySpark validation expressions from the Pydantic models.
# The expressions/generated/ tree is not committed to git, and `uv build`
# packages whatever is on disk under the module root, so this must run
# before building or packaging this package or the wheel ships without it.
#
# Invoked as a package-owned convention: CI runs this generically (see
# .github/workflows/main-publish.yaml and release-publish.yaml) as
# `packages/<package>/scripts/prebuild.sh`, if the file exists, before
# `uv build --package <package>`. Neither workflow needs to know pyspark is
# special; every other package simply has no prebuild.sh.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

output_dir="packages/overture-schema-pyspark/src/overture/schema/pyspark/expressions/generated"
rm -rf "$output_dir"
uv run overture-codegen generate --format pyspark --output-dir "$output_dir"

# Guard against a silently empty tree: if codegen ever regresses to produce
# nothing, fail loudly here instead of shipping a hollow package to PyPI.
if ! find "$output_dir" -name '*.py' -print -quit | grep -q .; then
  echo "::error::No expressions generated under ${output_dir} -- codegen produced nothing." >&2
  exit 1
fi
