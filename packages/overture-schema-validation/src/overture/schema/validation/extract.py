"""Extract validation rules from Pydantic model classes into the validation IR."""

from __future__ import annotations

import enum
from typing import Any, Literal, get_args, get_origin

import annotated_types
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic.types import Strict

from .ir import CheckType, Condition, DatasetSpec, Rule, Severity, ValidationSpec

# Fields to skip during extraction — they are structural, not data-validation targets.
_SKIPPED_FIELDS: frozenset[str] = frozenset({"theme", "type", "bbox", "sources"})

# Storage primitive NewType names whose constraints should be skipped in favor of
# domain-level constraints layered on top of them.
_STORAGE_PRIMITIVES: frozenset[str] = frozenset(
    {"int8", "int16", "int32", "int64", "uint8", "uint16", "uint32"}
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract(model_class: type[BaseModel], dataset_name: str | None = None) -> DatasetSpec:
    """Extract validation rules from a single Pydantic model class."""
    dataset_name = dataset_name or _get_dataset_name(model_class)
    rules: list[Rule] = []

    for field_name, field_info in model_class.model_fields.items():
        if field_name in _SKIPPED_FIELDS or field_name.startswith("ext_"):
            continue
        col_name = field_info.alias or field_name
        rules += _extract_field_rules(
            dataset_name, col_name, field_info, column_prefix="", parent_is_optional=False
        )

    rules += _extract_model_constraint_rules(model_class, dataset_name)

    return DatasetSpec(
        name=dataset_name,
        source_model=f"{model_class.__module__}.{model_class.__qualname__}",
        id_column="id",
        rules=rules,
    )


def extract_all(namespace: str | None = None) -> ValidationSpec:
    """Extract rules from all registered models via ``discover_models()``."""
    from overture.schema.core.discovery import discover_models

    models = discover_models(namespace=namespace)
    datasets = []
    for model_class in models.values():
        if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
            continue
        datasets.append(extract(model_class))
    return ValidationSpec(datasets=datasets)


# ---------------------------------------------------------------------------
# Dataset name detection
# ---------------------------------------------------------------------------


def _get_dataset_name(model_class: type[BaseModel]) -> str:
    """Derive the dataset name from the model's ``type`` Literal field."""
    field_info = model_class.model_fields.get("type")
    if field_info is not None:
        annotation = field_info.annotation
        origin = get_origin(annotation)
        if origin is Literal:
            args = get_args(annotation)
            if args:
                return str(args[0])
    # Fallback: lowercase class name
    return model_class.__name__.lower()


# ---------------------------------------------------------------------------
# Field-level rule extraction
# ---------------------------------------------------------------------------


def _extract_field_rules(
    dataset: str,
    field_name: str,
    field_info: FieldInfo,
    *,
    column_prefix: str,
    parent_is_optional: bool,
    list_columns: list[str] | None = None,
) -> list[Rule]:
    """Extract rules for a single field, recursing into nested BaseModel fields."""
    column = f"{column_prefix}{field_name}" if column_prefix else field_name
    rules: list[Rule] = []

    raw_annotation = field_info.annotation
    base_type, collected_metadata, domain_kwargs, is_nullable, is_list = _collect_constraints(
        raw_annotation
    )

    # Two categories of list_columns for rules:
    # - lc_container: list-level checks (not_null, min/max_length from model
    #   metadata, unique, geometry_type) — uses the parent list boundary only
    # - lc_element: element-level checks (numeric, enum/in, literal, pattern,
    #   is_type, min/max_length from effective_kwargs inner type) — adds this
    #   column as an additional list boundary when is_list
    lc_container = list_columns or None
    if is_list:
        lc_element = (list_columns or []) + [column]
    else:
        lc_element = list_columns or None

    # Merge model-level Field() metadata into the picture. Model-level metadata
    # (from field_info.metadata) takes priority over NewType chain metadata.
    model_metadata = list(field_info.metadata)
    model_numeric = _extract_numeric_kwargs(model_metadata)

    # Use model-level numeric kwargs if present; otherwise fall back to domain.
    effective_kwargs = model_numeric if model_numeric else domain_kwargs

    # ---- not_null ----
    is_required = field_info.is_required() and not is_nullable
    if is_required and not parent_is_optional:
        rules.append(
            _rule(dataset, column, "not_null", CheckType.NOT_NULL,
                  list_columns=lc_container)
        )
    elif is_required and parent_is_optional:
        rules.append(
            _rule(
                dataset,
                column,
                "not_null",
                CheckType.NOT_NULL,
                list_columns=lc_container,
                when=Condition(column=column_prefix.rstrip("."), check=CheckType.NOT_NULL),
            )
        )

    # ---- numeric range rules ----
    rules += _numeric_rules(dataset, column, effective_kwargs,
                            list_columns=lc_element)

    # ---- MinLen / MaxLen from model metadata ----
    for obj in model_metadata:
        if isinstance(obj, annotated_types.MinLen):
            if is_list:
                rules.append(
                    _rule(
                        dataset, column, "min_list_length", CheckType.MIN_LIST_LENGTH,
                        value=obj.min_length, list_columns=lc_container,
                    )
                )
            else:
                rules.append(
                    _rule(
                        dataset, column, "min_length", CheckType.MIN_LENGTH,
                        value=obj.min_length, list_columns=lc_container,
                    )
                )
        elif isinstance(obj, annotated_types.MaxLen):
            if is_list:
                rules.append(
                    _rule(
                        dataset, column, "max_list_length", CheckType.MAX_LIST_LENGTH,
                        value=obj.max_length, list_columns=lc_container,
                    )
                )
            else:
                rules.append(
                    _rule(
                        dataset, column, "max_length", CheckType.MAX_LENGTH,
                        value=obj.max_length, list_columns=lc_container,
                    )
                )

    # Also check effective kwargs for min_length / max_length (from Field())
    if "min_length" in effective_kwargs and not any(
        isinstance(obj, annotated_types.MinLen) for obj in model_metadata
    ):
        rules.append(
            _rule(
                dataset, column, "min_length", CheckType.MIN_LENGTH,
                value=effective_kwargs["min_length"], list_columns=lc_element,
            )
        )
    if "max_length" in effective_kwargs and not any(
        isinstance(obj, annotated_types.MaxLen) for obj in model_metadata
    ):
        rules.append(
            _rule(
                dataset, column, "max_length", CheckType.MAX_LENGTH,
                value=effective_kwargs["max_length"], list_columns=lc_element,
            )
        )

    # ---- Strict bool → is_type "boolean" ----
    for obj in model_metadata:
        if isinstance(obj, Strict) and obj.strict:
            if _is_bool_type(base_type):
                rules.append(
                    _rule(
                        dataset, column, "type", CheckType.IS_TYPE,
                        value="boolean", list_columns=lc_element,
                    )
                )

    # ---- Enum → in ----
    enum_type = _get_enum_type(base_type)
    if enum_type is not None:
        sorted_values = sorted(m.value for m in enum_type)
        rules.append(
            _rule(
                dataset,
                column,
                "valid",
                CheckType.IN,
                value=sorted_values,
                list_columns=lc_element,
            )
        )

    # ---- Literal → eq or in ----
    if get_origin(base_type) is Literal:
        lit_args = get_args(base_type)
        if len(lit_args) == 1:
            rules.append(
                _rule(
                    dataset, column, CheckType.EQ.value, CheckType.EQ,
                    value=lit_args[0], list_columns=lc_element,
                )
            )
        elif len(lit_args) > 1:
            rules.append(
                _rule(
                    dataset, column, "valid", CheckType.IN,
                    value=sorted(lit_args), list_columns=lc_element,
                )
            )

    # ---- GeometryTypeConstraint ----
    all_metadata = model_metadata + collected_metadata
    # Deduplicate by type to avoid e.g. UniqueItemsConstraint appearing from both sources
    seen_constraint_types: set[str] = set()
    for obj in all_metadata:
        if _is_geometry_type_constraint(obj):
            type_name = type(obj).__name__
            if type_name not in seen_constraint_types:
                seen_constraint_types.add(type_name)
                geo_values = [t.geo_json_type for t in obj.allowed_types]
                rules.append(
                    _rule(dataset, column, "type", CheckType.GEOMETRY_TYPE,
                          value=geo_values, list_columns=lc_container)
                )

    # ---- PatternConstraint / StrippedConstraint ----
    for obj in all_metadata:
        if _is_stripped_constraint(obj):
            type_name = type(obj).__name__
            if type_name not in seen_constraint_types:
                seen_constraint_types.add(type_name)
                rules.append(
                    _rule(
                        dataset, column, "pattern", CheckType.PATTERN,
                        value=r"^(\S.*)?\S$", list_columns=lc_element,
                    )
                )
        elif _is_pattern_constraint(obj):
            type_name = type(obj).__name__
            if type_name not in seen_constraint_types:
                seen_constraint_types.add(type_name)
                rules.append(
                    _rule(
                        dataset, column, "pattern", CheckType.PATTERN,
                        value=obj.pattern.pattern, list_columns=lc_element,
                    )
                )

    # ---- UniqueItemsConstraint ----
    for obj in all_metadata:
        if _is_unique_items_constraint(obj):
            type_name = type(obj).__name__
            if type_name not in seen_constraint_types:
                seen_constraint_types.add(type_name)
                rules.append(_rule(dataset, column, "unique", CheckType.UNIQUE,
                                   list_columns=lc_container))

    # ---- Nested BaseModel → recurse ----
    if isinstance(base_type, type) and issubclass(base_type, BaseModel) and not _is_enum_type(base_type):
        nested_is_optional = is_nullable or parent_is_optional
        # Build list_columns for children: if this field is itself a list,
        # add this column to the list boundary chain.
        child_list_columns = (list_columns or []) + [column] if is_list else list_columns
        for nested_name, nested_info in base_type.model_fields.items():
            if nested_name in _SKIPPED_FIELDS or nested_name.startswith("ext_"):
                continue
            nested_col_name = nested_info.alias or nested_name
            rules += _extract_field_rules(
                dataset,
                nested_col_name,
                nested_info,
                column_prefix=f"{column}.",
                parent_is_optional=nested_is_optional,
                list_columns=child_list_columns,
            )

    return rules


# ---------------------------------------------------------------------------
# Model constraint extraction
# ---------------------------------------------------------------------------


def _extract_model_constraint_rules(
    model_class: type[BaseModel], dataset: str
) -> list[Rule]:
    """Convert model-level constraints to IR rules."""
    try:
        from overture.schema.system.model_constraint.model_constraint import ModelConstraint
        from overture.schema.system.model_constraint.require_any_of import RequireAnyOfConstraint
        from overture.schema.system.model_constraint.radio_group import RadioGroupConstraint
        from overture.schema.system.model_constraint.require_if import RequireIfConstraint
        from overture.schema.system.model_constraint.forbid_if import ForbidIfConstraint
        from overture.schema.system.model_constraint.no_extra_fields import NoExtraFieldsConstraint
    except ImportError:
        return []

    constraints = ModelConstraint.get_model_constraints(model_class)
    rules: list[Rule] = []
    # Track name occurrences to ensure uniqueness
    name_counts: dict[str, int] = {}

    def _unique_name(base_name: str) -> str:
        count = name_counts.get(base_name, 0)
        name_counts[base_name] = count + 1
        if count == 0:
            return base_name
        return f"{base_name}_{count}"

    for constraint in constraints:
        if isinstance(constraint, NoExtraFieldsConstraint):
            continue

        if isinstance(constraint, RequireAnyOfConstraint):
            columns = list(constraint.field_names)
            rule_name = f"{dataset}.any_of"
            # Deduplicate: append field names for uniqueness
            rule_name = f"{dataset}.{'_'.join(columns)}.any_of"
            rules.append(
                Rule(
                    name=rule_name,
                    columns=columns,
                    check=CheckType.ANY_OF,
                    severity=Severity.ERROR,
                )
            )

        elif isinstance(constraint, RadioGroupConstraint):
            columns = list(constraint.field_names)
            rule_name = f"{dataset}.{'_'.join(columns)}.exactly_one_of"
            rules.append(
                Rule(
                    name=rule_name,
                    columns=columns,
                    check=CheckType.EXACTLY_ONE_OF,
                    severity=Severity.ERROR,
                )
            )

        elif isinstance(constraint, RequireIfConstraint):
            when = _convert_condition(constraint.condition)
            for field_name in constraint.field_names:
                base_name = f"{dataset}.{field_name}.required_when"
                rules.append(
                    Rule(
                        name=_unique_name(base_name),
                        column=field_name,
                        check=CheckType.NOT_NULL,
                        when=when,
                        severity=Severity.ERROR,
                    )
                )

        elif isinstance(constraint, ForbidIfConstraint):
            when = _convert_condition(constraint.condition)
            for field_name in constraint.field_names:
                base_name = f"{dataset}.{field_name}.forbidden_when"
                rules.append(
                    Rule(
                        name=_unique_name(base_name),
                        column=field_name,
                        check=CheckType.IS_NULL,
                        when=when,
                        severity=Severity.ERROR,
                    )
                )

    return rules


# ---------------------------------------------------------------------------
# Condition conversion
# ---------------------------------------------------------------------------


def _convert_condition(condition: Any) -> Condition:
    """Convert a system Condition to an IR Condition."""
    from overture.schema.system.model_constraint.model_constraint import (
        FieldEqCondition,
        Not,
    )

    if isinstance(condition, Not):
        inner = condition.inner
        if isinstance(inner, FieldEqCondition):
            value = inner.value.value if isinstance(inner.value, enum.Enum) else inner.value
            return Condition(column=inner.field_name, check=CheckType.NEQ, value=value)
        raise ValueError(f"Unsupported negated condition type: {type(inner)}")

    if isinstance(condition, FieldEqCondition):
        value = condition.value.value if isinstance(condition.value, enum.Enum) else condition.value
        return Condition(column=condition.field_name, check=CheckType.EQ, value=value)

    raise ValueError(f"Unsupported condition type: {type(condition)}")


# ---------------------------------------------------------------------------
# NewType / Annotated unwrapping
# ---------------------------------------------------------------------------


def _collect_constraints(
    annotation: Any,
) -> tuple[Any, list[Any], dict[str, Any], bool, bool]:
    """Walk the annotation chain collecting constraints.

    Returns
    -------
    (base_type, metadata_objects, domain_kwargs, is_nullable, is_list)
    """
    is_nullable = False
    is_list = False

    # Strip Optional (X | None)
    annotation, is_nullable = _strip_optional(annotation)

    # Strip list[X]
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        if args:
            annotation = args[0]
            is_list = True
            # The inner type may itself be Optional
            annotation, inner_nullable = _strip_optional(annotation)
            is_nullable = is_nullable or inner_nullable

    # Walk NewType / Annotated chain
    layers: list[tuple[str, list[Any], dict[str, Any]]] = []
    _walk_annotation(annotation, layers)

    # Collect all metadata objects across layers
    all_metadata: list[Any] = []
    for _, meta, _ in layers:
        all_metadata.extend(meta)

    # Select domain constraints: first non-storage-primitive layer with kwargs
    domain_kwargs: dict[str, Any] = {}
    for name, _, kwargs in layers:
        if name not in _STORAGE_PRIMITIVES and kwargs:
            domain_kwargs = kwargs
            break

    # Find the base type (innermost)
    base = annotation
    for name, _, _ in reversed(layers):
        pass  # just traversing
    # Actually resolve the base by walking all the way down
    base = _resolve_base_type(annotation)

    return base, all_metadata, domain_kwargs, is_nullable, is_list


def _walk_annotation(annotation: Any, layers: list[tuple[str, list[Any], dict[str, Any]]]) -> None:
    """Recursively walk a NewType/Annotated annotation, collecting layers."""
    from typing import Annotated

    # Check for NewType
    supertype = getattr(annotation, "__supertype__", None)
    if supertype is not None:
        name = getattr(annotation, "__name__", "unknown")
        # If the supertype is Annotated, extract its metadata
        if get_origin(supertype) is Annotated:
            args = get_args(supertype)
            inner = args[0]
            meta_objects = list(args[1:])
            kwargs = _extract_field_kwargs(meta_objects)
            layers.append((name, [obj for obj in meta_objects if not isinstance(obj, FieldInfo)], kwargs))
            _walk_annotation(inner, layers)
        else:
            layers.append((name, [], {}))
            _walk_annotation(supertype, layers)
        return

    # Check for Annotated directly
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        inner = args[0]
        meta_objects = list(args[1:])
        kwargs = _extract_field_kwargs(meta_objects)
        layers.append(("annotated", [obj for obj in meta_objects if not isinstance(obj, FieldInfo)], kwargs))
        _walk_annotation(inner, layers)
        return


def _resolve_base_type(annotation: Any) -> Any:
    """Resolve the ultimate base type through NewType/Annotated chains."""
    from typing import Annotated

    supertype = getattr(annotation, "__supertype__", None)
    if supertype is not None:
        return _resolve_base_type(supertype)

    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        return _resolve_base_type(args[0])

    return annotation


def _extract_field_kwargs(meta_objects: list[Any]) -> dict[str, Any]:
    """Extract numeric kwargs from FieldInfo objects in metadata."""
    kwargs: dict[str, Any] = {}
    for obj in meta_objects:
        if isinstance(obj, FieldInfo):
            for attr in ("ge", "gt", "le", "lt", "min_length", "max_length"):
                val = getattr(obj.metadata, attr, None) if hasattr(obj.metadata, attr) else None
                if val is None:
                    # FieldInfo stores these in its own metadata list
                    for m in (obj.metadata or []):
                        v = getattr(m, attr, None) if hasattr(m, attr) else None
                        if v is not None:
                            kwargs[attr] = v
                else:
                    kwargs[attr] = val
    return kwargs


def _extract_numeric_kwargs(metadata: list[Any]) -> dict[str, Any]:
    """Extract numeric constraint kwargs from annotated_types metadata objects."""
    kwargs: dict[str, Any] = {}
    for obj in metadata:
        if isinstance(obj, annotated_types.Ge):
            kwargs["ge"] = obj.ge
        elif isinstance(obj, annotated_types.Gt):
            kwargs["gt"] = obj.gt
        elif isinstance(obj, annotated_types.Le):
            kwargs["le"] = obj.le
        elif isinstance(obj, annotated_types.Lt):
            kwargs["lt"] = obj.lt
    return kwargs


# ---------------------------------------------------------------------------
# Numeric rule generation
# ---------------------------------------------------------------------------


def _numeric_rules(
    dataset: str, column: str, kwargs: dict[str, Any],
    list_columns: list[str] | None = None,
) -> list[Rule]:
    """Generate numeric comparison rules from kwargs dict."""
    rules: list[Rule] = []
    ge = kwargs.get("ge")
    le = kwargs.get("le")
    gt = kwargs.get("gt")
    lt = kwargs.get("lt")

    # between: only when both ge and le are present and no gt/lt
    if ge is not None and le is not None and gt is None and lt is None:
        rules.append(
            _rule(dataset, column, "range", CheckType.BETWEEN, value=[ge, le],
                  list_columns=list_columns)
        )
    else:
        if ge is not None:
            rules.append(_rule(dataset, column, CheckType.GTE.value, CheckType.GTE, value=ge,
                               list_columns=list_columns))
        if le is not None:
            rules.append(_rule(dataset, column, CheckType.LTE.value, CheckType.LTE, value=le,
                               list_columns=list_columns))
        if gt is not None:
            rules.append(_rule(dataset, column, CheckType.GT.value, CheckType.GT, value=gt,
                               list_columns=list_columns))
        if lt is not None:
            rules.append(_rule(dataset, column, CheckType.LT.value, CheckType.LT, value=lt,
                               list_columns=list_columns))

    return rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule(
    dataset: str,
    column: str,
    suffix: str,
    check: CheckType,
    value: Any = None,
    list_columns: list[str] | None = None,
    when: Condition | None = None,
) -> Rule:
    """Create a Rule with a standardised name."""
    return Rule(
        name=f"{dataset}.{column}.{suffix}",
        column=column,
        check=check,
        value=value,
        list_columns=list_columns,
        when=when,
        severity=Severity.ERROR,
    )


def _strip_optional(annotation: Any) -> tuple[Any, bool]:
    """Strip ``X | None`` → ``(X, True)``; otherwise ``(annotation, False)``."""
    import types

    origin = get_origin(annotation)

    # Handle Union types (X | None)
    if origin is types.UnionType:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return non_none[0], True
        return annotation, False

    # Also handle typing.Union
    import typing

    if origin is typing.Union:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return non_none[0], True
        return annotation, False

    return annotation, False


def _is_bool_type(t: Any) -> bool:
    """Check if the base type is bool."""
    return t is bool


def _is_enum_type(t: Any) -> bool:
    """Check if a type is an Enum subclass."""
    return isinstance(t, type) and issubclass(t, enum.Enum)


def _get_enum_type(t: Any) -> type[enum.Enum] | None:
    """Return the Enum class if t is an Enum subclass, else None."""
    if isinstance(t, type) and issubclass(t, enum.Enum):
        return t
    return None


def _is_geometry_type_constraint(obj: Any) -> bool:
    return type(obj).__name__ == "GeometryTypeConstraint"


def _is_pattern_constraint(obj: Any) -> bool:
    return type(obj).__name__ in (
        "PatternConstraint",
        "HexColorConstraint",
        "CountryCodeAlpha2Constraint",
        "NoWhitespaceConstraint",
        "SnakeCaseConstraint",
        "LanguageTagConstraint",
        "PhoneNumberConstraint",
        "RegionCodeConstraint",
        "WikidataIdConstraint",
    )


def _is_stripped_constraint(obj: Any) -> bool:
    return type(obj).__name__ == "StrippedConstraint"


def _is_unique_items_constraint(obj: Any) -> bool:
    return type(obj).__name__ == "UniqueItemsConstraint"
