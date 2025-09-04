# GERS Sidecar Match Example

## What is Hatchling?

**Hatchling** is a modern Python build backend that provides a robust and extensible way to build Python packages. It's the default build backend for projects that use `pyproject.toml` configuration files and follows the PEP 517/PEP 518 standards for Python packaging.

### Key features of Hatchling:
- **Standards Compliant**: Follows modern Python packaging standards (PEP 517, PEP 518, PEP 621)
- **Fast and Lightweight**: Designed for performance with minimal dependencies
- **Extensible**: Plugin system for custom build logic
- **Wheel and Source Distribution Support**: Can build both wheel (.whl) and source (.tar.gz) distributions
- **Metadata Management**: Handles package metadata, versioning, and dependencies automatically

### Why use Hatchling for this project?
This GERS examples project now uses Hatchling as its build backend to:
1. **Standardize packaging**: Provides a consistent way to install and distribute the code
2. **Manage dependencies**: Automatically handles the geospatial Python dependencies
3. **Enable easy installation**: Users can install with `pip install -e .` for development
4. **Provide command-line tools**: The `match-traces` command is automatically available after installation

## Installation

You can now install this package in development mode using:

```bash
cd gers/examples/python
pip install -e .
```

This will install the package and its dependencies, making the `match-traces` command available in your environment.

## Context

Consumers of geospatial data sets usually need to solve a complex and costly process of matching them.
A data set that also has GERS IDs can be easily used to augment the Overture data set itself, or other data sets that also have GERS IDs via simple join by id.

Because Overture data sets are modeled and produced with prioritizing for stability of its identifiers (GERS IDs) over time, and the cost of matching being offset to the owner of the data sets, the consumers of data sets with GERS IDs can conflate, evaluate and onboard such feeds much cheaper and faster.

## Purpose

Matching a geospatial data set with overture (or any other) data set is a common problem and many solutions exist for this, from generic to highly specialized for particular data types. 

Depending on the match requirements, this can be achieved with a open source or commercial tools or services, with a few click or couple of lines of code or with large scale distributed system with complex match logic. 

Main purpose is to provide an example of how to start exploring a data set's compatibility with overture data set and to find GERS IDs that correspond to its features.

## Example
[Snap GPS traces to overture roads](MATCH_TRACES.md)

