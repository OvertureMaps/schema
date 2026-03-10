"""Shared test fixtures for CLI tests."""

from collections.abc import Generator

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> Generator[CliRunner, None, None]:
    """Provide a CliRunner within an isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner
