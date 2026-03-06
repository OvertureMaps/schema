"""Pytest plugin: ``--update-baselines`` option and ``update_baselines`` fixture.

Activated by consuming packages via ``[project.entry-points.pytest11]`` in
their ``pyproject.toml``. Importing this module is a no-op outside pytest.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the ``--update-baselines`` CLI option."""
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Regenerate baseline golden files instead of comparing",
    )


@pytest.fixture
def update_baselines(request: pytest.FixtureRequest) -> bool:
    """Whether to regenerate baseline files instead of comparing."""
    return bool(request.config.getoption("--update-baselines"))
