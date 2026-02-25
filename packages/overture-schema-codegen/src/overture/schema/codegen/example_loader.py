"""Load and process example data from theme pyproject.toml files."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from .model_extraction import resolve_field_alias
from .type_analyzer import single_literal_value

log = logging.getLogger(__name__)

__all__ = ["ExampleRecord", "load_examples", "validate_example"]

# tomllib is stdlib from 3.11+; tomli is the backport for 3.10.
try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[import-not-found]


@dataclass
class ExampleRecord:
    """A flattened example with field-value pairs in documentation order."""

    rows: list[tuple[str, Any]]


def _inject_literal_fields(
    model_fields_dict: dict[str, FieldInfo], data: dict[str, Any]
) -> dict[str, Any]:
    """Inject single-value Literal field defaults missing from *data*.

    Inspects *model_fields_dict* for fields with single-value ``Literal``
    annotations. For each field missing from *data*, injects the literal
    value using the field's ``validation_alias`` (if set), falling back
    to ``alias``, then to the field name.

    Returns a new dict; the original is not mutated.
    """
    result = data.copy()

    for field_name, field_info in model_fields_dict.items():
        key = resolve_field_alias(field_name, field_info)
        if key in result:
            continue

        literal_value = single_literal_value(field_info.annotation)
        if literal_value is not None:
            result[key] = literal_value

    return result


def _denull_value(value: object) -> object:
    """Convert a single value, replacing ``"null"`` strings with ``None``."""
    if value == "null":
        return None
    if isinstance(value, dict):
        return _denull(value)
    if isinstance(value, list):
        return [_denull_value(item) for item in value]
    return value


def _denull(data: dict[str, Any]) -> dict[str, Any]:
    """Convert ``"null"`` sentinel strings to ``None``.

    TOML has no null literal, so example data uses the string ``"null"``
    as a stand-in.  This recursively walks *data* (including nested dicts,
    lists of dicts, and plain lists) and replaces every ``"null"`` value
    with ``None``.

    Returns a new dict; the original is not mutated.
    """
    return {key: _denull_value(value) for key, value in data.items()}


def _known_field_keys(model_fields_dict: dict[str, FieldInfo]) -> frozenset[str]:
    """Alias-resolved field keys from a model_fields dict."""
    return frozenset(
        resolve_field_alias(name, info) for name, info in model_fields_dict.items()
    )


def _strip_null_unknown_fields(
    data: dict[str, Any], known_keys: frozenset[str]
) -> dict[str, Any]:
    """Drop null-valued fields not in *known_keys*.

    For discriminated unions, *known_keys* contains only common base
    fields.  Variant-specific null fields from other arms (present in
    flat parquet schemas) are stripped so the selected arm's validator
    doesn't reject them as unknown extras.

    Non-null fields are always kept so the arm's own validator can
    accept or reject them normally.
    """
    return {k: v for k, v in data.items() if v is not None or k in known_keys}


def validate_example(
    validation_type: object,
    raw: dict[str, Any],
    *,
    model_fields: dict[str, FieldInfo] | None = None,
) -> dict[str, Any]:
    """Validate example data against a model or union type.

    Uses TypeAdapter for validation, supporting both concrete models
    and discriminated union aliases.

    Preprocesses *raw* data by:
    1. Converting "null" strings to None
    2. Injecting missing Literal fields for validation (if model_fields provided)
    3. Stripping null-valued fields not in *model_fields* (handles
       flat-schema examples from discriminated unions where fields from
       non-selected arms appear as nulls)

    Returns the denulled dict (not the preprocessed one with injected
    literals). Lets ValidationError propagate on validation failure.
    """
    denulled = _denull(raw)

    if model_fields is None:
        if isinstance(validation_type, type) and issubclass(validation_type, BaseModel):
            model_fields = validation_type.model_fields
        else:
            model_fields = {}

    known_keys = _known_field_keys(model_fields)
    preprocessed = _inject_literal_fields(model_fields, denulled)
    preprocessed = _strip_null_unknown_fields(preprocessed, known_keys)
    TypeAdapter(validation_type).validate_python(preprocessed)
    return denulled


_DEFAULT_SKIP_KEYS: frozenset[str] = frozenset({"bbox"})


def _flatten_value(prefix: str, value: object) -> list[tuple[str, Any]]:
    """Recursively flatten a value into dot/bracket-notation rows."""
    if isinstance(value, dict):
        result: list[tuple[str, Any]] = []
        for k, v in value.items():
            result.extend(_flatten_value(f"{prefix}.{k}", v))
        return result
    if isinstance(value, list) and value and isinstance(value[0], (dict, list)):
        result = []
        for i, item in enumerate(value):
            result.extend(_flatten_value(f"{prefix}[{i}]", item))
        return result
    return [(prefix, value)]


def flatten_example(
    raw: dict[str, Any],
    *,
    skip_keys: frozenset[str] = _DEFAULT_SKIP_KEYS,
) -> list[tuple[str, Any]]:
    """Flatten nested example dict to dot-notation key-value pairs.

    Nested dicts become ``"parent.child"``; lists of dicts become
    ``"parent[0].child"``; lists of lists of dicts use double-index
    notation ``"parent[0][1].child"``. Keys in *skip_keys* are dropped
    at the top level only. Plain lists are kept as values.
    """
    result: list[tuple[str, Any]] = []
    for key, value in raw.items():
        if key in skip_keys:
            continue
        result.extend(_flatten_value(key, value))
    return result


def extract_base_field(key: str) -> str:
    """Extract the top-level field name from a flattened key.

    >>> extract_base_field("sources[0].dataset")
    'sources'
    >>> extract_base_field("names.primary")
    'names'
    >>> extract_base_field("id")
    'id'
    """
    if "[" in key:
        return key.split("[")[0]
    if "." in key:
        return key.split(".")[0]
    return key


def order_example_rows(
    flat_rows: list[tuple[str, Any]],
    field_names: list[str],
) -> list[tuple[str, Any]]:
    """Order flattened rows by field position in documentation.

    Sorts by position of base field name in *field_names*.
    Fields with the same base maintain their original order (stable sort).
    Unknown fields sort to end.
    """
    position = {name: i for i, name in enumerate(field_names)}
    sentinel = len(field_names)

    def sort_key(row: tuple[str, Any]) -> int:
        return position.get(extract_base_field(row[0]), sentinel)

    return sorted(flat_rows, key=sort_key)


def load_examples_from_toml(
    pyproject_path: Path,
    model_name: str,
) -> list[dict[str, Any]]:
    """Load ``[examples.<model_name>]`` from a pyproject.toml file."""
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    examples: dict[str, list[dict[str, Any]]] = data.get("examples", {})
    return examples.get(model_name, [])


def resolve_pyproject_path(model_class: type) -> Path | None:
    """Find pyproject.toml by walking up from the model's module location."""
    module_name = getattr(model_class, "__module__", None)
    if not module_name:
        return None

    module = sys.modules.get(module_name)
    if not module:
        return None

    module_file = getattr(module, "__file__", None)
    if not module_file:
        return None

    # Walk up from module directory
    current = Path(module_file).parent
    while current != current.parent:  # Stop at filesystem root
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            return pyproject
        current = current.parent

    return None


def load_examples(
    validation_type: object,
    model_name: str,
    field_names: list[str],
    *,
    pyproject_source: type | None = None,
    model_fields: dict[str, FieldInfo] | None = None,
) -> list[ExampleRecord]:
    """Load examples for a model, flattened and ordered by *field_names*.

    Validates each example against the validation type. Invalid examples
    are skipped with a warning logged. Returns an empty list on any failure
    (missing file, missing section, parse error).

    Parameters
    ----------
    validation_type : type[BaseModel] | object
        Model class or union alias to validate against.
    model_name : str
        Name of the model to load examples for.
    field_names : list[str]
        List of field names for ordering output.
    pyproject_source : type or None
        Type to use for finding pyproject.toml. If None,
        uses validation_type if it's a class.
    model_fields : dict[str, FieldInfo] or None
        Field info dict for Literal injection. If None, infers
        from validation_type if it's a BaseModel class.
    """
    source_type = pyproject_source if pyproject_source is not None else validation_type
    if not isinstance(source_type, type):
        return []

    pyproject_path = resolve_pyproject_path(source_type)
    if not pyproject_path:
        return []

    try:
        raw_examples = load_examples_from_toml(pyproject_path, model_name)
    except (OSError, tomllib.TOMLDecodeError):
        log.debug("Failed to load examples for %s", model_name, exc_info=True)
        return []

    if not raw_examples:
        return []

    records = []
    for raw in raw_examples:
        try:
            denulled = validate_example(validation_type, raw, model_fields=model_fields)
        except ValidationError as e:
            log.warning(
                "Skipping invalid example for %s in %s: %s",
                model_name,
                pyproject_path,
                e,
            )
            continue
        flat_rows = flatten_example(denulled)
        ordered_rows = order_example_rows(flat_rows, field_names)
        records.append(ExampleRecord(rows=ordered_rows))

    return records
