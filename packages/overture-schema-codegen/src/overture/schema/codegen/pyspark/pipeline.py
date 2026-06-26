"""PySpark generation pipeline: produce modules without I/O.

Orchestrates check building, schema building, and rendering into
GeneratedModule objects. The caller decides what to do with them (write
to disk, stream to stdout, etc.).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from overture.schema.system.case import to_snake_case
from overture.schema.system.discovery import entry_point_to_path
from overture.schema.system.primitive import GeometryType

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

    The source and test trees are written to separate directories and
    mirror the same relative layout, so a path is meaningful only
    relative to its tree. Splitting at the boundary keeps each tree
    self-contained -- in practice the overlap today is just
    `__init__.py`, but any path duplicated between trees would be
    ambiguous in a single flat list.
    """

    source: list[GeneratedModule]
    test: list[GeneratedModule]


_OUTPUT_PACKAGE = "overture.schema.pyspark.expressions.generated"

# Dots in `from ...x import y` from a generated test module to reach
# `tests/`: one to leave the file's package, one to leave `generated/`.
# Each additional directory component under `generated/` adds another.
_DOTS_FROM_TEST_TO_TESTS_ROOT = 2


def _support_prefix(directory: PurePosixPath) -> str:
    """Relative-import prefix used by generated test modules to reach `_support`.

    Each leading dot climbs one package level; the first two dots step
    out of `tests/generated/` to `tests/`, and an extra dot is appended
    for every component of *directory* under `generated/`.
    """
    return "." * (len(directory.parts) + _DOTS_FROM_TEST_TO_TESTS_ROOT)


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


def _init_modules(paths: Iterable[PurePosixPath]) -> list[GeneratedModule]:
    """Emit empty `__init__.py` for every directory of `paths`.

    Includes the output root so the top-level package exists after a
    full `rm -rf` of the generated tree.
    """
    paths = list(paths)
    if not paths:
        return []
    dirs: set[PurePosixPath] = set()
    for path in paths:
        dirs.update(path.parents)
    return [GeneratedModule(content="", path=d / "__init__.py") for d in sorted(dirs)]


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
        Source-tree model modules and test-tree modules. Each tree
        includes the `__init__.py` files needed for its package layout.
    """
    items = [(spec, build_checks(spec)) for spec in model_specs]
    source = [_render_module(spec, checks) for spec, checks in items]
    test: list[GeneratedModule] = []
    for spec, checks in items:
        test.extend(_render_test_modules(spec, checks))
    source.extend(_init_modules(m.path for m in source))
    test.extend(_init_modules(m.path for m in test))
    return PipelineOutput(source=source, test=test)


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
    support_prefix = _support_prefix(directory)

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
                    support_prefix=support_prefix,
                ),
                path=directory / f"test_{model_name}{suffix}.py",
            )
        )
    return modules
