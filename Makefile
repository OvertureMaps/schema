.PHONY: default uv-sync clean-pyspark generate-pyspark verify-pyspark-generated check test-all test test-only docformat doctest doctest-only mypy mypy-only lint-only update-baselines

TESTMON ?= --testmon

default: test-all

install: uv-sync

uv-sync:
	@uv sync --all-packages --all-extras -q

PYSPARK_EXPRESSIONS := packages/overture-schema-pyspark/src/overture/schema/pyspark/expressions/generated
PYSPARK_GENERATED_TESTS := packages/overture-schema-pyspark/tests/generated

clean-pyspark:
	@rm -rf $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS)

generate-pyspark: uv-sync clean-pyspark
	@uv run overture-codegen generate --format pyspark \
		--output-dir $(PYSPARK_EXPRESSIONS) \
		--test-output-dir $(PYSPARK_GENERATED_TESTS)
	@uv run ruff check --fix --quiet $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS)
	@uv run ruff format --quiet $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS)

check: uv-sync generate-pyspark
	@$(MAKE) -j test-only doctest-only lint-only mypy-only

# Regenerate and fail if the committed generated output differs. Catches PRs
# that change the schema or codegen without committing the regenerated files --
# `check` itself regenerates, so without this guard stale committed output is
# silently overwritten before the tests run and never verified.
verify-pyspark-generated: generate-pyspark
	@git diff --exit-code -- $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS) \
		|| { echo "Generated PySpark output is stale; run 'make generate-pyspark' and commit."; exit 1; }

# test-all is the unconditional full run -- testmon-independent, unlike the
# incremental test/test-only targets -- so data-only changes (golden JSON,
# [[examples]]) that testmon cannot see still get exercised.
test-all: uv-sync
	@uv run pytest -W error packages/

test: uv-sync
	@uv run pytest -W error $(TESTMON) packages/ -x -q --tb=short

test-only:
	@uv run pytest -W error $(TESTMON) packages/ -x -q --tb=short

coverage: uv-sync
	@uv run pytest packages/ --cov overture.schema --cov-report=term --cov-report=html && open htmlcov/index.html

docformat:
	@find packages/*/src -name "*.py" -type f -not -name "__*" \
		| xargs uv run pydocstyle --convention=numpy --add-ignore=D102,D105,D200,D205,D400

doctest: uv-sync doctest-only

doctest-only:
	@# $$ escapes $ for make - sed needs literal $ for end-of-line anchor
	@find packages/*/src -name "*.py" -type f \
		| sed 's|^packages/[^/]*/src/||' \
		| sed 's|/|.|g' \
		| sed 's|\.py$$||' \
		| sed 's|\.__init__$$||' \
		| sed '/\.__.*__$$/d' \
		| sort -u \
		| xargs uv run python -c 'import doctest, importlib, sys; sys.exit(any(doctest.testmod(importlib.import_module(m)).failed for m in sys.argv[1:]))'

# mypy type checking with namespace package support
mypy: uv-sync mypy-only

mypy-only:
	@# $$ escapes $ for make - sed needs literal $ for end-of-line anchor
	@find packages -maxdepth 1 -type d -name "overture-schema*" \
		| sort \
		| sed 's|-theme$$||' \
		| tr - . \
		| sed 's|^packages/|-p |' \
		| xargs uv run mypy --no-error-summary
	@for d in packages/*/tests; do find "$$d" -name "*.py" | sort | xargs uv run mypy --no-error-summary || exit 1; done

lint-only:
	@uv run ruff check -q packages/
	@uv run ruff format --check packages/

update-baselines:
	@uv run pytest --update-baselines -m baseline -q packages/
