"""CLI subpackage for overture-schema."""

from .commands import (
    cli,
    create_union_type_from_models,
    handle_generic_error,
    handle_validation_error,
    load_input,
    perform_validation,
    resolve_types,
)
from .types import (
    ErrorLocation,
    ModelDict,
    UnionType,
    ValidationErrorDict,
)

__all__ = [
    "cli",
    "create_union_type_from_models",
    "handle_generic_error",
    "handle_validation_error",
    "load_input",
    "perform_validation",
    "resolve_types",
    "ErrorLocation",
    "ModelDict",
    "UnionType",
    "ValidationErrorDict",
]
