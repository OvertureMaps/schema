.PHONY: check test test-all mypy

default: test-all

check: test
	uv run ruff check packages/
	$(MAKE) mypy

test-all:
	uv run pytest packages/

test:
	uv run pytest packages/ -x

# mypy type checking with namespace package support
mypy:
	@cd packages && uv run mypy --namespace-packages \
		-p overture.schema \
		-p overture.schema.addresses \
		-p overture.schema.base \
		-p overture.schema.buildings \
		-p overture.schema.core \
		-p overture.schema.divisions \
		-p overture.schema.validation
	@uv run mypy packages/*/tests/*.py
