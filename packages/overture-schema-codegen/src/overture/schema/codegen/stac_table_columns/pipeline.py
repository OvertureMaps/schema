"""STAC `table:columns` generation pipeline: render documents without I/O.

One artifact per model -- a STAC Item properties fragment carrying the `table:`
fields -- and the gap log beside it, which for a target this thin is as much the
deliverable as the fragment.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from overture.schema.system.case import to_snake_case

from ..extraction.specs import ModelSpec
from .exceptions import TableColumnsGap
from .renderer import TABLE_EXTENSION_URI, render_table_columns

__all__ = ["TableColumnsOutput", "generate_table_columns_documents"]


@dataclass(frozen=True, slots=True)
class TableColumnsOutput:
    """A rendered STAC fragment and everything it could not hold."""

    model: str
    stac: str
    stac_path: PurePosixPath
    gaps: tuple[TableColumnsGap, ...]


def generate_table_columns_documents(
    model_specs: Sequence[ModelSpec],
) -> list[TableColumnsOutput]:
    """Render one STAC fragment per spec, plus the gap log."""
    outputs: list[TableColumnsOutput] = []
    for spec in model_specs:
        rendered = render_table_columns(spec)
        stem = to_snake_case(spec.name)
        # A bare properties fragment rather than a whole Item: the extension
        # fields are what this target emits, and an Item would need id, geometry,
        # bbox, datetime and links, none of which come from a schema.
        fragment = {
            "stac_extensions": [TABLE_EXTENSION_URI],
            "properties": rendered.stac_fields(),
        }
        outputs.append(
            TableColumnsOutput(
                model=spec.name,
                stac=json.dumps(fragment, indent=2) + "\n",
                stac_path=PurePosixPath(f"{stem}.json"),
                gaps=rendered.gaps,
            )
        )
    return outputs
