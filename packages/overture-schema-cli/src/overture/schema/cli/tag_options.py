"""Shared Click options for tag-based model selection."""

from collections.abc import Callable
from typing import TypeVar

import click

from overture.schema.system.discovery import TagSelector

F = TypeVar("F", bound=Callable[..., object])

_TAG_SYNTAX_NOTE = (
    "Accepts plain tags (e.g. feature), namespaced tags "
    "(e.g. overture:approved), or compound key/value tags "
    "(e.g. overture:theme=buildings)."
)


def tag_selection_options(func: F) -> F:
    """Decorate a Click command with --tag, --filter, and --exclude options.

    The decorated command receives `tags`, `filters`, and `excludes`
    keyword arguments (each a `tuple[str, ...]`), suitable for passing to
    `build_selector`.
    """
    func = click.option(
        "--exclude",
        "excludes",
        multiple=True,
        help=(
            "Exclude feature types with these tags — removes from scope (OR-NOT; "
            f"repeatable). {_TAG_SYNTAX_NOTE}"
        ),
    )(func)
    func = click.option(
        "--filter",
        "filters",
        multiple=True,
        help=(
            "Require feature types to have these tags — narrows scope (AND; "
            f"repeatable). {_TAG_SYNTAX_NOTE}"
        ),
    )(func)
    func = click.option(
        "--tag",
        "tags",
        multiple=True,
        help=(
            "Include feature types with these tags — defines scope (OR; repeatable). "
            f"{_TAG_SYNTAX_NOTE}"
        ),
    )(func)
    return func


def build_selector(
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
) -> TagSelector:
    """Map `tag_selection_options` arguments to a `TagSelector`."""
    return TagSelector(
        include_any=tags,
        require_all=filters,
        exclude_any=excludes,
    )
