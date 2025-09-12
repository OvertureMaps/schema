.PHONY: check test test-all mypy

default: test-all

check: test
	@uv run ruff check -q packages/
	@$(MAKE) mypy
	@uv run ruff format --check packages/

test-all:
	@uv run pytest packages/

test:
	@uv run pytest packages/ -x

# mypy type checking with namespace package support
mypy:
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
