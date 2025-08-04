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
	@uv run mypy packages/*/tests/*.py
