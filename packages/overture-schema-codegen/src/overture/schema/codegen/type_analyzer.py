"""Iterative type unwrapping for Pydantic model annotations."""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Sentinel

from .docstring import clean_docstring

__all__ = [
    "ConstraintSource",
    "TypeKind",
    "TypeInfo",
    "UnsupportedUnionError",
    "analyze_type",
    "is_newtype",
    "single_literal_value",
]


class UnsupportedUnionError(TypeError):
    """Raised when analyze_type encounters a multi-type union it cannot represent."""


class TypeKind(Enum):
    """Classification of type kinds."""

    PRIMITIVE = auto()
    LITERAL = auto()
    ENUM = auto()
    MODEL = auto()
    UNION = auto()


@dataclass(slots=True)
class ConstraintSource:
    """A constraint paired with the NewType that contributed it."""

    source: str | None
    constraint: object


@dataclass(slots=True)
class TypeInfo:
    """Information about a type annotation."""

    base_type: str
    kind: TypeKind
    is_optional: bool = False
    is_list: bool = False
    is_dict: bool = False
    dict_key_type: TypeInfo | None = None
    dict_value_type: TypeInfo | None = None
    constraints: tuple[ConstraintSource, ...] = ()
    literal_value: object | None = None
    source_type: type | None = None
    newtype_name: str | None = None
    newtype_ref: object | None = None
    union_members: tuple[type[BaseModel], ...] | None = None
    description: str | None = None


def is_newtype(annotation: object) -> bool:
    """Check if annotation is a typing.NewType.

    NewType creates a callable with a __supertype__ attribute pointing
    to the wrapped type. No public API exists for this check.
    """
    return callable(annotation) and hasattr(annotation, "__supertype__")


def _is_union(origin: object) -> bool:
    """Check if an origin represents a union type (X | Y or Union[X, Y])."""
    return origin in (types.UnionType, Union)


@dataclass(slots=True)
class _UnwrapState:
    """Accumulated state from iterative type unwrapping.

    Tracks two NewType names during unwrapping:
    - ``outermost_newtype_name`` / ``outermost_newtype_ref``: the first
      NewType encountered, exposed as ``TypeInfo.newtype_name`` / ``newtype_ref``.
    - ``last_newtype_name``: the most recently entered NewType, used both
      as constraint provenance (which NewType contributed each constraint)
      and as the resolved ``base_type`` for the terminal type.
    """

    is_optional: bool = False
    is_list: bool = False
    is_dict: bool = False
    dict_key_type: TypeInfo | None = None
    dict_value_type: TypeInfo | None = None
    constraints: list[ConstraintSource] = field(default_factory=list)
    outermost_newtype_name: str | None = None
    outermost_newtype_ref: object | None = None
    last_newtype_name: str | None = None
    description: str | None = None

    def add_constraint(self, source: str | None, constraint: object) -> None:
        self.constraints.append(ConstraintSource(source, constraint))

    def build_type_info(
        self,
        *,
        base_type: str,
        kind: TypeKind,
        literal_value: object | None = None,
        source_type: type | None = None,
        union_members: tuple[type[BaseModel], ...] | None = None,
    ) -> TypeInfo:
        return TypeInfo(
            base_type=base_type,
            kind=kind,
            is_optional=self.is_optional,
            is_list=self.is_list,
            is_dict=self.is_dict,
            dict_key_type=self.dict_key_type,
            dict_value_type=self.dict_value_type,
            constraints=tuple(self.constraints),
            literal_value=literal_value,
            source_type=source_type,
            newtype_name=self.outermost_newtype_name,
            newtype_ref=self.outermost_newtype_ref,
            union_members=union_members,
            description=self.description,
        )


def analyze_type(annotation: object) -> TypeInfo:
    """Analyze a type annotation and return TypeInfo.

    Iteratively unwraps type wrappers (Annotated, Optional, list, NewType) until
    reaching a terminal type.
    """
    state = _UnwrapState()

    while True:
        origin = get_origin(annotation)

        # Handle NewType (e.g., int32 = NewType("int32", Annotated[int, ...]))
        if is_newtype(annotation):
            name = annotation.__name__  # type: ignore[attr-defined]
            state.last_newtype_name = name
            if state.outermost_newtype_name is None:
                state.outermost_newtype_name = name
                state.outermost_newtype_ref = annotation
            annotation = annotation.__supertype__  # type: ignore[attr-defined]
            continue

        # Handle Annotated types (Annotated[X, metadata...])
        if origin is Annotated:
            args = get_args(annotation)
            annotation = args[0]
            for c in args[1:]:
                if isinstance(c, FieldInfo):
                    if c.description is not None and state.description is None:
                        state.description = clean_docstring(c.description)
                    for m in c.metadata:
                        state.add_constraint(state.last_newtype_name, m)
                else:
                    state.add_constraint(state.last_newtype_name, c)
            continue

        # Handle union types (X | None or Optional[X])
        if _is_union(origin):
            args = get_args(annotation)
            # Filter out None, Sentinel types (Pydantic's <MISSING>), and
            # Literal alternatives (e.g., HttpUrl | Literal[""] where the
            # Literal is a special-value sentinel, not the primary type).
            if any(a is types.NoneType for a in args):
                state.is_optional = True

            non_none_args = [
                a
                for a in args
                if a is not types.NoneType and not isinstance(a, Sentinel)
            ]

            # Only filter out Literal arms when a concrete (non-Literal) type
            # exists.  Without this guard, Optional[Literal["x"]] would lose
            # all args because the Literal *is* the primary type.
            concrete_args = [a for a in non_none_args if get_origin(a) is not Literal]
            real_args = concrete_args if concrete_args else non_none_args

            if len(real_args) > 1:
                # Check if all real args are BaseModel subclasses
                # (unwrap Annotated wrappers to get the actual class)
                members: list[type[BaseModel]] = []
                for arg in real_args:
                    inner = arg
                    if get_origin(inner) is Annotated:
                        inner = get_args(inner)[0]
                    if isinstance(inner, type) and issubclass(inner, BaseModel):
                        members.append(inner)
                    else:
                        raise UnsupportedUnionError(
                            f"Multi-type unions not supported: {annotation}"
                        )
                return state.build_type_info(
                    base_type=members[0].__name__,
                    kind=TypeKind.UNION,
                    union_members=tuple(members),
                )

            if not real_args:
                raise UnsupportedUnionError(
                    f"Union with no concrete types: {annotation}"
                )

            annotation = real_args[0]
            continue

        # Handle list types (list[X])
        if origin is list:
            args = get_args(annotation)
            if not args:
                raise TypeError("Bare list without type argument is not supported")
            state.is_list = True
            annotation = args[0]
            continue

        # Handle dict types (dict[K, V])
        if origin is dict:
            args = get_args(annotation)
            if not args:
                raise TypeError("Bare dict without type arguments is not supported")
            state.is_dict = True
            state.dict_key_type = analyze_type(args[0])
            state.dict_value_type = analyze_type(args[1])
            base_type = state.last_newtype_name or "dict"
            return state.build_type_info(
                base_type=base_type,
                kind=TypeKind.PRIMITIVE,
                source_type=dict,
            )

        break

    return _classify_terminal(annotation, state)


def _classify_terminal(annotation: object, state: _UnwrapState) -> TypeInfo:
    """Classify a fully-unwrapped terminal type into a TypeInfo."""
    # typing.Any -- treat as an opaque primitive
    if annotation is Any:
        return state.build_type_info(
            base_type="Any",
            kind=TypeKind.PRIMITIVE,
        )

    # Literal types (e.g., Literal["value"])
    if get_origin(annotation) is Literal:
        args = get_args(annotation)
        # Only expose literal_value for single-value Literals, which
        # represent fixed constants (theme="buildings"). Multi-value
        # Literals (Literal["a", "b"]) are enum-like and have no
        # single default.
        value = args[0] if len(args) == 1 else None
        return state.build_type_info(
            base_type="Literal",
            kind=TypeKind.LITERAL,
            literal_value=value,
        )

    if not isinstance(annotation, type):
        raise TypeError(f"Unsupported annotation type: {type(annotation)}")

    if issubclass(annotation, list):
        raise TypeError("Bare list without type argument is not supported")

    if issubclass(annotation, dict):
        raise TypeError("Bare dict without type arguments is not supported")

    # Determine kind from type hierarchy
    if issubclass(annotation, Enum):
        kind = TypeKind.ENUM
    elif issubclass(annotation, BaseModel):
        kind = TypeKind.MODEL
    else:
        kind = TypeKind.PRIMITIVE

    base_type = state.last_newtype_name or annotation.__name__

    return state.build_type_info(
        base_type=base_type,
        kind=kind,
        source_type=annotation,
    )


def single_literal_value(annotation: object) -> object | None:
    """Extract a single literal value from a type annotation, or None.

    Delegates to analyze_type for all unwrapping, then checks
    whether the result is a single-value Literal.
    """
    try:
        ti = analyze_type(annotation)
    except (TypeError, UnsupportedUnionError):
        return None
    if ti.kind == TypeKind.LITERAL:
        return ti.literal_value
    return None
