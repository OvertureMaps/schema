# Overture Schema

Pydantic schemas for Overture Maps data structures.

## Overview

This project provides type-safe Python models for validating and working with [Overture Maps Foundation](https://overturemaps.org) data.

## Project Structure

This is a multi-package workspace that will contain theme-based packages for different types of Overture data.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Install dependencies
uv sync

# Run tests
make test

# Code quality
uv run ruff check .
uv run ruff format .
make mypy
```
