# What is a Hatchling?

## Overview

**Hatchling** is a modern Python build backend that serves as the build system for this project. It's the tool responsible for packaging Python code into distributable formats like wheels (.whl files) and source distributions (.tar.gz files).

## What is a Build Backend?

A build backend is a tool that:
- Converts your Python source code into a package that can be installed
- Handles dependencies and metadata
- Creates distribution files (wheels and source distributions)
- Ensures your package follows Python packaging standards

## Why Hatchling?

Hatchling was chosen for this project because it:

### 1. **Modern Standards Compliance**
- Follows PEP 517 (Build System Interface) and PEP 518 (Build System Requirements)
- Uses `pyproject.toml` for configuration instead of legacy `setup.py`
- Implements PEP 621 (Project Metadata in pyproject.toml)

### 2. **Performance**
- Fast build times with minimal dependencies
- Efficient wheel building process
- Lightweight runtime footprint

### 3. **Simplicity**
- Declarative configuration in `pyproject.toml`
- No need for complex `setup.py` scripts
- Automatic handling of common packaging tasks

### 4. **Extensibility**
- Plugin system for custom build logic
- Flexible configuration options
- Integration with modern Python tooling

## How It Works in This Project

This project uses hatchling through the `pyproject.toml` configuration file:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Key Configuration Elements:

1. **Package Metadata**: Name, version, description, authors
2. **Dependencies**: Required packages for the geospatial functionality
3. **Entry Points**: Command-line scripts (like `match-traces`)
4. **Build Targets**: What files to include in distributions

## Commands You Can Use

With hatchling configured, you can:

```bash
# Install in development mode
pip install -e .

# Build a wheel
python -m build --wheel

# Build a source distribution
python -m build --sdist

# Build both
python -m build
```

## Benefits for Users

- **Easy Installation**: `pip install overture-gers-examples`
- **Command Line Tools**: The `match-traces` command becomes available
- **Dependency Management**: All required packages are installed automatically
- **Standard Packaging**: Works with all standard Python packaging tools

## Relationship to GERS

GERS (Global Entity Reference System) is the data identification system used by Overture Maps. Hatchling packages the Python tools that work with GERS data, making them easy to distribute and install for users who want to:

- Match GPS traces to road segments
- Work with Overture Maps data
- Use GERS identifiers in their own applications

## Further Reading

- [Hatchling Documentation](https://hatch.pypa.io/latest/)
- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [Python Packaging User Guide](https://packaging.python.org/)