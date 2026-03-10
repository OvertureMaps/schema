"""Load, validate, and flatten example data for schema documentation."""

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

__all__ = [
    "ExampleRecord",
    "augment_missing_fields",
    "flatten_model_instance",
    "load_examples",
    "validate_example",
]

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
) -> BaseModel:
    """Validate example data against a model or union type.

    Returns the validated model instance. Preprocesses *raw* data by:
    1. Injecting missing Literal fields for validation (if model_fields provided)
    2. Stripping null-valued fields not in *model_fields* (handles
       flat-schema examples from discriminated unions)
    """
    if model_fields is None:
        if isinstance(validation_type, type) and issubclass(validation_type, BaseModel):
            model_fields = validation_type.model_fields
        else:
            model_fields = {}

    known_keys = _known_field_keys(model_fields)
    preprocessed = _inject_literal_fields(model_fields, raw)
    preprocessed = _strip_null_unknown_fields(preprocessed, known_keys)
    result: BaseModel = TypeAdapter(validation_type).validate_python(preprocessed)
    assert isinstance(result, BaseModel)
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


def _structured_fields(value: object) -> list[tuple[str, Any]] | None:
    """Extract named fields from ``__slots__``-based types like BBox.

    Returns a list of ``(name, value)`` pairs for types that expose
    public properties backed by private slots (``_name`` -> ``name``).
    Returns ``None`` for types without this pattern.
    """
    cls = type(value)
    slots = getattr(cls, "__slots__", ())
    if not slots:
        return None
    fields: list[tuple[str, Any]] = []
    for slot in slots:
        attr = slot.lstrip("_")
        if attr != slot and isinstance(getattr(cls, attr, None), property):
            fields.append((attr, getattr(value, attr)))
    return fields if len(fields) >= 2 else None


def _needs_recursion(items: list[Any]) -> bool:
    """Check whether list items contain models or nested lists."""
    return bool(items) and isinstance(items[0], (BaseModel, list))


def _flatten_list_items(key: str, items: list[Any]) -> list[tuple[str, Any]]:
    """Flatten list items, recursing into BaseModel and nested list items.

    Returns the list as a single leaf value when no items need recursion.
    Pydantic model fields produce homogeneous lists, so the first item's
    type determines the flattening strategy.
    """
    if not _needs_recursion(items):
        return [(key, items)]
    rows: list[tuple[str, Any]] = []
    for i, item in enumerate(items):
        if isinstance(item, BaseModel):
            rows.extend(flatten_model_instance(item, f"{key}[{i}]."))
        elif isinstance(item, list):
            rows.extend(_flatten_list_items(f"{key}[{i}]", item))
        else:
            rows.append((f"{key}[{i}]", item))
    return rows


def flatten_model_instance(
    instance: BaseModel,
    prefix: str = "",
) -> list[tuple[str, Any]]:
    """Flatten a Pydantic model instance to dot-notation key-value pairs.

    Walks model fields recursively. BaseModel values recurse with dot
    notation, lists of BaseModel recurse with bracket notation, and
    everything else (dicts, primitives, None) is a leaf value.

    Parameters
    ----------
    instance
        The Pydantic model instance to flatten.
    prefix
        Dot-notation prefix accumulated from parent fields.

    Returns
    -------
    list[tuple[str, Any]]
        Flattened key-value pairs in field declaration order.
    """
    rows: list[tuple[str, Any]] = []
    for field_name, field_info in type(instance).model_fields.items():
        key = resolve_field_alias(field_name, field_info)
        value = getattr(instance, field_name)
        full_key = f"{prefix}{key}" if prefix else key

        if isinstance(value, BaseModel):
            rows.extend(flatten_model_instance(value, f"{full_key}."))
        elif isinstance(value, list):
            rows.extend(_flatten_list_items(full_key, value))
        elif (sub_fields := _structured_fields(value)) is not None:
            for name, v in sub_fields:
                rows.append((f"{full_key}.{name}", v))
        else:
            rows.append((full_key, value))
    return rows


def augment_missing_fields(
    rows: list[tuple[str, Any]],
    field_names: list[str],
) -> list[tuple[str, Any]]:
    """Add (name, None) entries for fields absent from *rows*.

    Compares base field names (via ``extract_base_field``) against
    *field_names*. Fields in *field_names* not represented in *rows*
    are appended as ``(name, None)``. Handles dot-notation and bracket-
    notation keys correctly.

    Parameters
    ----------
    rows
        Flattened key-value pairs from a concrete model instance.
    field_names
        Merged field name list from the union spec.

    Returns
    -------
    list[tuple[str, Any]]
        Original rows with (name, None) entries appended for absent fields.
    """
    present = {extract_base_field(key) for key, _ in rows}
    augmented = list(rows)
    for name in field_names:
        if name not in present:
            augmented.append((name, None))
    return augmented


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
            instance = validate_example(validation_type, raw, model_fields=model_fields)
        except ValidationError as e:
            log.warning(
                "Skipping invalid example for %s in %s: %s",
                model_name,
                pyproject_path,
                e,
            )
            continue
        flat_rows = flatten_model_instance(instance)
        flat_rows = augment_missing_fields(flat_rows, field_names)
        ordered_rows = order_example_rows(flat_rows, field_names)
        records.append(ExampleRecord(rows=ordered_rows))

    return records
