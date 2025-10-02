.PHONY: default uv-sync check test-all test mypy reset-baseline-schemas

default: test-all

uv-sync:
	@uv sync --all-packages

check: test doctest
	@uv run ruff check -q packages/
	@$(MAKE) mypy
	@uv run ruff format --check packages/

test-all: uv-sync
	@uv run pytest packages/

test: uv-sync
	@uv run pytest packages/ -x

docformat:
	@find packages/*/src -name "*.py" -type f -not -name "__*" \
		| xargs uv run pydocstyle --convention=numpy --add-ignore=D105

doctest: uv-sync
	@# $$ escapes $ for make - sed needs literal $ for end-of-line anchor
	@find packages/*/src -name "*.py" -type f -not -name "__*" \
		| sed 's|^packages/[^/]*/src/||' \
		| sed 's|/|.|g' \
		| sed 's|\.py$$||' \
		| xargs uv run python -c 'import doctest, importlib, sys; [doctest.testmod(importlib.import_module(m)) for m in sys.argv[1:]]'

# mypy type checking with namespace package support
mypy: uv-sync
	@cd packages && uv run mypy --no-error-summary --namespace-packages \
		-p overture.schema \
		-p overture.schema.addresses \
		-p overture.schema.base \
		-p overture.schema.buildings \
		-p overture.schema.core \
		-p overture.schema.divisions \
		-p overture.schema.places \
		-p overture.schema.transportation \
		-p overture.schema.validation
	@uv run mypy --no-error-summary packages/*/tests/*.py

reset-baseline-schemas:
	@find . -name \*_baseline_schema.json -delete
