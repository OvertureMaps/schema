.PHONY: default uv-sync check test-all test docformat doctest mypy reset-baseline-schemas

default: test-all

uv-sync:
	@uv sync --all-packages 2> /dev/null

check: test doctest
	@uv run ruff check -q packages/
	@$(MAKE) mypy
	@uv run ruff format --check packages/

test-all: uv-sync
	@uv run pytest -W error packages/

test: uv-sync
	@uv run pytest -W error packages/ -x

coverage: uv-sync
	@uv run pytest packages/ --cov overture.schema --cov-report=term --cov-report=html && open htmlcov/index.html

docformat:
	@find packages/*/src -name "*.py" -type f -not -name "__*" \
		| xargs uv run pydocstyle --convention=numpy --add-ignore=D102,D105,D200,D205,D400

doctest: uv-sync
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
mypy: uv-sync
	@# $$ escapes $ for make - sed needs literal $ for end-of-line anchor
	@find packages -maxdepth 1 -type d -name "overture-schema*" \
		| sort \
		| sed 's|-theme$$||' \
		| tr - . \
		| sed 's|^packages/|-p |' \
		| xargs uv run mypy --no-error-summary
	@uv run mypy --no-error-summary packages/*/tests/*.py

reset-baseline-schemas:
	@find . -name \*_baseline_schema.json -delete
