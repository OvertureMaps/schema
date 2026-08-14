"""PySpark generation pipeline: produce modules without I/O.

Orchestrates check building, schema building, and rendering into
GeneratedModule objects. The caller decides what to do with them (write
to disk, stream to stdout, etc.).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from overture.schema.system.case import to_snake_case
from overture.schema.system.discovery import entry_point_to_path
from overture.schema.system.geometric import GeometryType

from ..extraction.specs import ModelSpec, UnionSpec
from .check_builder import build_checks
from .check_ir import Check, ModelCheck
from .renderer import render_model_module
from .schema_builder import build_schema
from .test_data.base_row import (
    generate_arm_rows,
    generate_base_row,
    generate_populated_arm_rows,
    generate_populated_row,
)
from .test_renderer import render_test_module

__all__ = [
    "GeneratedModule",
    "PipelineOutput",
    "generate_pyspark_module",
    "generate_pyspark_modules",
]


@dataclass(frozen=True, slots=True)
class GeneratedModule:
    """A generated Python module with its content and output path."""

    content: str
    path: PurePosixPath


@dataclass(frozen=True, slots=True)
class PipelineOutput:
    """PySpark modules emitted by the pipeline, split by output tree.

    Source and test modules write to separate directories
    (`--output-dir` and `--test-output-dir`), so they travel as two
    lists rather than one. Both trees mirror the same relative layout,
    so a path is meaningful only relative to its own tree.
    """

    source: list[GeneratedModule]
    test: list[GeneratedModule]


_OUTPUT_PACKAGE = "overture.schema.pyspark.expressions.generated"

_INDEX_PATH = PurePosixPath("_index.py")

_INDEX_DOCSTRING = '''"""Index of the generated validation modules.

The runtime registry imports this module and reads ``MODULES``. Because that is
an ordinary import, discovery works even when the package is loaded from a wheel
on ``sys.path`` (zipimport), as AWS Glue does via ``--extra-py-files``, where the
generated modules are reachable by import but not as files on disk.
"""'''


def _require_entry_point(spec: ModelSpec) -> str:
    """Return *spec*'s entry point or raise if it's missing."""
    if spec.entry_point is None:
        msg = f"ModelSpec {spec.name!r} has no entry_point."
        raise ValueError(msg)
    return spec.entry_point


def _directory_and_model_name(spec: ModelSpec) -> tuple[PurePosixPath, str]:
    """Return the output directory and snake_case model name for a spec.

    Both halves derive from the entry-point's class name so filenames
    and symbol names stay in sync with what the runtime registry
    discovers.
    """
    directory, cls_name = entry_point_to_path(_require_entry_point(spec))
    return directory, to_snake_case(cls_name)


def _extract_geometry_types(
    field_checks: list[Check],
) -> tuple[GeometryType, ...]:
    """Collect allowed geometry types from every `check_geometry_type` descriptor.

    A model may carry multiple `check_geometry_type` descriptors -- e.g.
    one per union arm with a distinct allowed-types set. The result is the
    union of all of them, sorted by name for deterministic output.
    """
    seen: set[GeometryType] = set()
    for check in field_checks:
        for desc in check.descriptors:
            if desc.function != "check_geometry_type":
                continue
            for arg in desc.args:
                if isinstance(arg, GeometryType):
                    seen.add(arg)
    return tuple(sorted(seen, key=lambda g: g.name))


def generate_pyspark_module(spec: ModelSpec) -> GeneratedModule:
    """Generate a PySpark validation module from a model spec.

    Parameters
    ----------
    spec
        The extracted model spec to generate from.

    Returns
    -------
    GeneratedModule
        Module content and a relative output path mirroring the
        model's entry-point package layout.
    """
    return _render_module(spec, build_checks(spec))


def generate_pyspark_modules(
    model_specs: Sequence[ModelSpec],
) -> PipelineOutput:
    """Generate PySpark validation modules for all models.

    Parameters
    ----------
    model_specs
        Extracted model specs to generate from.

    Returns
    -------
    PipelineOutput
        Source-tree model modules plus an `_index` module listing them,
        and test-tree modules. The index is an ordinary `_index.py`, so the
        generated tree stays PEP 420 and its namespace packages are untouched.
    """
    items = [(spec, build_checks(spec)) for spec in model_specs]
    source = [_render_module(spec, checks) for spec, checks in items]
    if source:
        source.append(_render_index(model_specs))
    test: list[GeneratedModule] = []
    for spec, checks in items:
        test.extend(_render_test_modules(spec, checks))
    return PipelineOutput(source=source, test=test)


def _render_index(model_specs: Sequence[ModelSpec]) -> GeneratedModule:
    """Render the `_index` module listing every generated validation module.

    The runtime registry imports the generated modules through this index, so
    the codegen owns which modules exist. Each is aliased by its full dotted
    path so two feature types with the same leaf name cannot collide.
    """
    entries = sorted(
        (
            ".".join([_OUTPUT_PACKAGE, *directory.parts]),
            model_name,
            "_".join([*directory.parts, model_name]),
        )
        for directory, model_name in (
            _directory_and_model_name(spec) for spec in model_specs
        )
    )
    lines = [
        "# This file is auto-generated by overture-schema-codegen. Do not edit.",
        _INDEX_DOCSTRING,
        "",
        "from __future__ import annotations",
        "",
        *(f"from {parent} import {leaf} as {alias}" for parent, leaf, alias in entries),
        "",
        "MODULES = (",
        *(f"    {alias}," for _, _, alias in entries),
        ")",
        "",
    ]
    return GeneratedModule(content="\n".join(lines), path=_INDEX_PATH)


def _render_module(
    spec: ModelSpec,
    checks: tuple[list[Check], list[ModelCheck]],
) -> GeneratedModule:
    """Build checks, schema, and render for a model spec."""
    field_checks, model_checks = checks
    schema_fields = build_schema(spec)
    geometry_types = _extract_geometry_types(field_checks)
    directory, model_name = _directory_and_model_name(spec)
    content = render_model_module(
        model_name,
        field_checks,
        model_checks,
        schema_fields,
        geometry_types,
        entry_point=_require_entry_point(spec),
        partitions=spec.partitions,
    )
    return GeneratedModule(
        content=content,
        path=directory / f"{model_name}.py",
    )


def _select_arm_rows(
    spec: ModelSpec,
) -> dict[str | None, tuple[dict[str, object], dict[str, object]]]:
    """Map each test module's arm key to its (sparse, populated) base rows.

    Multi-arm unions key by discriminator value (one entry per arm); other
    specs use a single `None` key. Either way the caller iterates the dict
    to emit one test module per entry.
    """
    if isinstance(spec, UnionSpec) and spec.discriminator_field:
        sparse_arm_rows = generate_arm_rows(spec)
        populated_arm_rows = generate_populated_arm_rows(spec)
        return {
            arm: (sparse_arm_rows[arm], populated_arm_rows[arm])
            for arm in sparse_arm_rows
        }
    return {None: (generate_base_row(spec), generate_populated_row(spec))}


def _render_test_modules(
    spec: ModelSpec,
    checks: tuple[list[Check], list[ModelCheck]],
) -> list[GeneratedModule]:
    """Render test modules for a model spec.

    For union specs with multiple discriminator arms, produces one
    test module per arm. Each arm's test includes the field and
    model checks tagged with that arm (or untagged), filtered by
    `render_test_module`.
    """
    field_checks, model_checks = checks
    directory, model_name = _directory_and_model_name(spec)
    expression_import = ".".join([_OUTPUT_PACKAGE, *directory.parts, model_name])

    modules: list[GeneratedModule] = []
    for arm, (base_row_sparse, base_row_populated) in _select_arm_rows(spec).items():
        suffix = f"_{arm}" if arm is not None else ""
        modules.append(
            GeneratedModule(
                content=render_test_module(
                    model_name,
                    field_checks,
                    model_checks,
                    base_row_sparse=base_row_sparse,
                    base_row_populated=base_row_populated,
                    arm=arm,
                    spec=spec,
                    expression_import=expression_import,
                ),
                path=directory / f"test_{model_name}{suffix}.py",
            )
        )
    return modules
