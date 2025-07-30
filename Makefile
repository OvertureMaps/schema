# Dynamically find packages with tests
PACKAGES_WITH_TESTS := $(shell find packages -maxdepth 2 -name tests -type d | cut -d'/' -f2 | sort -u)
TEST_TARGETS := $(addprefix test-, $(PACKAGES_WITH_TESTS))

.PHONY: check test test-all $(TEST_TARGETS)

default: test-all

check: test
	uv run ruff check
	$(MAKE) mypy

# Test target that continues on failure
test-all:
	@failed=0; \
	for target in $(TEST_TARGETS); do \
		echo "Running $$target"; \
		$(MAKE) $$target || failed=$$((failed + 1)); \
	done; \
	if [ $$failed -gt 0 ]; then \
		echo "$$failed test target(s) failed"; \
		exit 1; \
	fi

# Top-level test target that runs all package tests
test: $(TEST_TARGETS)

# Dynamic test targets for each package
$(TEST_TARGETS): test-%:
	@echo "Running tests in packages/$*"
	@cd packages/$* && uv run pytest

# mypy type checking with namespace package support
mypy:
	@echo "Running mypy type checking"
	@cd packages && uv run mypy --namespace-packages \
		-p overture.schema \
		-p overture.schema.addresses \
		-p overture.schema.base \
		-p overture.schema.core \
		-p overture.schema.validation
