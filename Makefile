.PHONY: default uv-sync check test-all test docformat doctest mypy reset-baseline-schemas \
       publish publish-all publish-core publish-system publish-annex publish-themes publish-cli publish-meta

default: test-all

# Publish all packages in dependency order
publish-all: publish-core publish-system publish-annex publish-themes publish-cli publish-meta
	@echo "All packages published successfully!"

# Level 0: No internal dependencies
publish-core:
	@echo "Publishing overture-schema-core..."
	uv build --package overture-schema-core
	uv publish --index overture dist/overture_schema_core-*.whl dist/overture_schema_core-*.tar.gz
	@rm -rf dist/overture_schema_core-*

publish-system:
	@echo "Publishing overture-schema-system..."
	uv build --package overture-schema-system
	uv publish --index overture dist/overture_schema_system-*.whl dist/overture_schema_system-*.tar.gz
	@rm -rf dist/overture_schema_system-*

# Level 1: Depends on core
publish-annex: publish-core
	@echo "Publishing overture-schema-annex..."
	uv build --package overture-schema-annex
	uv publish --index overture dist/overture_schema_annex-*.whl dist/overture_schema_annex-*.tar.gz
	@rm -rf dist/overture_schema_annex-*

publish-themes: publish-core
	@echo "Publishing theme packages..."
	uv build --package overture-schema-addresses-theme
	uv publish --index overture dist/overture_schema_addresses_theme-*.whl dist/overture_schema_addresses_theme-*.tar.gz
	@rm -rf dist/overture_schema_addresses_theme-*
	uv build --package overture-schema-base-theme
	uv publish --index overture dist/overture_schema_base_theme-*.whl dist/overture_schema_base_theme-*.tar.gz
	@rm -rf dist/overture_schema_base_theme-*
	uv build --package overture-schema-buildings-theme
	uv publish --index overture dist/overture_schema_buildings_theme-*.whl dist/overture_schema_buildings_theme-*.tar.gz
	@rm -rf dist/overture_schema_buildings_theme-*
	uv build --package overture-schema-divisions-theme
	uv publish --index overture dist/overture_schema_divisions_theme-*.whl dist/overture_schema_divisions_theme-*.tar.gz
	@rm -rf dist/overture_schema_divisions_theme-*
	uv build --package overture-schema-places-theme
	uv publish --index overture dist/overture_schema_places_theme-*.whl dist/overture_schema_places_theme-*.tar.gz
	@rm -rf dist/overture_schema_places_theme-*
	uv build --package overture-schema-transportation-theme
	uv publish --index overture dist/overture_schema_transportation_theme-*.whl dist/overture_schema_transportation_theme-*.tar.gz
	@rm -rf dist/overture_schema_transportation_theme-*

publish-cli: publish-core
	@echo "Publishing overture-schema-cli..."
	uv build --package overture-schema-cli
	uv publish --index overture dist/overture_schema_cli-*.whl dist/overture_schema_cli-*.tar.gz
	@rm -rf dist/overture_schema_cli-*

# Level 2: Meta-package depends on all others
publish-meta: publish-themes publish-cli
	@echo "Publishing overture-schema (meta-package)..."
	uv build --package overture-schema
	uv publish --index overture dist/overture_schema-*.whl dist/overture_schema-*.tar.gz
	@rm -rf dist/overture_schema-*

# Convenience alias
publish: publish-all

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
	@for d in packages/*/tests; do find "$$d" -name "*.py" | sort | xargs uv run mypy --no-error-summary || exit 1; done

reset-baseline-schemas:
	@find . -name \*_baseline_schema.json -delete
