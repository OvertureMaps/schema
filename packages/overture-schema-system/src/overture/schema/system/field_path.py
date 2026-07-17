"""Structural representation of a field path through a nested schema.

A `FieldPath` is one of three variants:

- `ScalarPath` -- a sequence of `StructSegment` values locating a value
  that requires no iteration to reach.
- `ArrayPath` -- a sequence of `StructSegment` and `ArraySegment` values,
  with at least one `ArraySegment`, locating a value reached by iterating
  one or more arrays. Each `ArraySegment` carries `iter_count`, the number
  of `[]` markers on its name in the canonical encoding (multi-depth
  segments encode nested-list iteration without an intervening struct,
  e.g. `list[list[X]]` parses as a single `ArraySegment` with
  `iter_count=2`).
- `MapPath` -- struct segments leading to a map column, a single
  `MapSegment` projecting the map to its keys or values, then a struct-only
  leaf (possibly empty). Locates a value reached by iterating a
  `dict[K, V]`'s keys or values, encoded with a `{key}` / `{value}` marker
  on the map column and the leaf appended after it (e.g. `names.common{key}`
  for a scalar value, `subs{value}.label` for a field inside a
  `dict[K, Model]` value).

The canonical string form (`str(path)`) round-trips through `parse`.
Code that needs to emit a path into source or labels calls `str(path)`
at the boundary; everything else operates on segments.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

__all__ = [
    "ArrayPath",
    "ArraySegment",
    "FieldPath",
    "FieldSegment",
    "MapPath",
    "MapProjection",
    "MapSegment",
    "ScalarPath",
    "StructSegment",
    "coerce",
    "parse",
    "promote_terminal_array",
    "promote_terminal_map",
]


@dataclass(frozen=True, slots=True)
class StructSegment:
    """A struct field navigation step."""

    name: str


@dataclass(frozen=True, slots=True)
class ArraySegment:
    """An array column entered with one or more levels of iteration.

    `iter_count` records the number of `[]` markers immediately following
    the segment name; values > 1 correspond to nested lists like
    `list[list[X]]`.
    """

    name: str
    iter_count: int = 1


class MapProjection(Enum):
    """Which side of a `dict[K, V]` a `MapSegment` iterates."""

    KEY = "key"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class MapSegment:
    """A map column entered by projecting to its keys or values.

    `projection` selects keys or values; the projected side is iterated
    like an array, so checks on a `MapSegment` render through the same
    element machinery as `ArraySegment`.
    """

    name: str
    projection: MapProjection


@dataclass(frozen=True, slots=True)
class ScalarPath:
    """Locate a non-iterated value in a row."""

    segments: tuple[StructSegment, ...] = ()

    def append_struct(self, name: str) -> ScalarPath:
        return ScalarPath(segments=self.segments + (StructSegment(name=name),))

    def append_array(self, name: str, iter_count: int = 1) -> ArrayPath:
        return ArrayPath(
            segments=self.segments + (ArraySegment(name=name, iter_count=iter_count),)
        )

    def __str__(self) -> str:
        return ".".join(s.name for s in self.segments)


@dataclass(frozen=True, slots=True)
class ArrayPath:
    """Locate an iterated value; iteration structure is part of the location.

    Invariant: `segments` contains at least one `ArraySegment`.
    """

    segments: tuple[StructSegment | ArraySegment, ...]

    def __post_init__(self) -> None:
        if not any(isinstance(s, ArraySegment) for s in self.segments):
            raise ValueError("ArrayPath must contain at least one ArraySegment")

    def append_struct(self, name: str) -> ArrayPath:
        return ArrayPath(segments=self.segments + (StructSegment(name=name),))

    def append_array(self, name: str, iter_count: int = 1) -> ArrayPath:
        return ArrayPath(
            segments=self.segments + (ArraySegment(name=name, iter_count=iter_count),)
        )

    @property
    def column_prefix(self) -> ScalarPath:
        """Struct segments before the first ArraySegment.

        Returns an empty `ScalarPath(())` when the array is the first
        segment.
        """
        prefix: list[StructSegment] = []
        for seg in self.segments:
            if isinstance(seg, ArraySegment):
                break
            prefix.append(seg)
        return ScalarPath(segments=tuple(prefix))

    @property
    def column_path(self) -> str:
        """Dotted name of the outermost array column.

        The struct prefix plus the first ArraySegment's name (unbracketed).
        This is what `F.col(...)` or `array_check("...", ...)` consumes.
        """
        first_prefix, first_array, _first_iter = self.array_chunks[0]
        return ".".join((*first_prefix, first_array))

    @property
    def leaf(self) -> tuple[str, ...]:
        """Names of struct segments after the last ArraySegment."""
        last_array = next(
            i
            for i in range(len(self.segments) - 1, -1, -1)
            if isinstance(self.segments[i], ArraySegment)
        )
        return tuple(s.name for s in self.segments[last_array + 1 :])

    @property
    def array_chunks(
        self,
    ) -> tuple[tuple[tuple[str, ...], str, int], ...]:
        """One chunk per ArraySegment.

        Each entry is `(prefix_structs, array_name, iter_count)` where
        `prefix_structs` is the sequence of struct segment names between
        the previous ArraySegment (or the start of the path) and this
        ArraySegment.
        """
        chunks: list[tuple[tuple[str, ...], str, int]] = []
        prefix: list[str] = []
        for seg in self.segments:
            if isinstance(seg, ArraySegment):
                chunks.append((tuple(prefix), seg.name, seg.iter_count))
                prefix = []
            else:
                prefix.append(seg.name)
        return tuple(chunks)

    def element_relative_gate(self, gate: FieldPath) -> tuple[str, ...] | None:
        """Path inside this array's element scope that names *gate*.

        Three return states:

        - ``tuple[str, ...]`` (non-empty) -- "reachable with descent":
          `gate` enters the same outer array as this path and names a
          struct descendant inside its element. The returned segments
          name that descendant relative to the element.
        - ``()`` -- "reachable, no descent": `gate` is the outer array
          itself; the element variable IS the gated value.
        - ``None`` -- "not reachable": `gate` does not cross into this
          path's element scope (different outer array, scalar gate,
          mismatched struct prefix, mismatched boundary `iter_count`,
          etc.). Callers must apply the gate at column level instead.

        Raises `NotImplementedError` when `gate` enters the same outer
        array but contains a nested `ArraySegment` past the boundary;
        the element scope is a struct, so a gate path inside it must be
        struct-only.

        Example: `parse("items[].x").element_relative_gate(parse(
        "items[].nested")) == ("nested",)`.
        """
        column_prefix = self.column_prefix.segments
        n_prefix = len(column_prefix)
        if not isinstance(gate, ArrayPath):
            return None
        gate_segs = gate.segments
        if len(gate_segs) <= n_prefix:
            return None
        for i in range(n_prefix):
            if not isinstance(gate_segs[i], StructSegment):
                return None
            if gate_segs[i].name != column_prefix[i].name:
                return None
        target_boundary = self.segments[n_prefix]
        assert isinstance(target_boundary, ArraySegment)
        gate_boundary = gate_segs[n_prefix]
        if not isinstance(gate_boundary, ArraySegment):
            return None
        if gate_boundary.name != target_boundary.name:
            return None
        if gate_boundary.iter_count != target_boundary.iter_count:
            return None
        inner_segments = gate_segs[n_prefix + 1 :]
        for seg in inner_segments:
            if not isinstance(seg, StructSegment):
                raise NotImplementedError(
                    f"gate path contains a nested array segment past the "
                    f"element boundary (gate={gate!r}, self={self!r})"
                )
        return tuple(s.name for s in inner_segments)

    @property
    def iter_struct_paths(self) -> tuple[tuple[str, ...], ...]:
        """Per non-outermost iteration: the struct path that reaches its array.

        For each ArraySegment past the first, emit `(prefix_structs +
        array_name)` -- the navigation FROM the previous iteration's
        element TO this array. For each `iter_count > 1` on an
        ArraySegment, emit `iter_count - 1` additional `()` entries
        representing extra iterations inside the same (already-named)
        array.

        Returns an empty tuple when the path iterates only once.
        """
        paths: list[tuple[str, ...]] = []
        for chunk_idx, (prefix_structs, arr_name, iter_count) in enumerate(
            self.array_chunks
        ):
            if chunk_idx > 0:
                paths.append(prefix_structs + (arr_name,))
            for _ in range(iter_count - 1):
                paths.append(())
        return tuple(paths)

    def __str__(self) -> str:
        return ".".join(_segment_str(s) for s in self.segments)


@dataclass(frozen=True, slots=True)
class MapPath:
    """Locate a value inside a map's keys or values via one `MapSegment`.

    Invariant: `segments` is a struct prefix, exactly one `MapSegment`
    boundary, then a struct-only leaf (possibly empty). The `MapSegment`
    iterates the projected keys or values like an array; the leaf navigates
    structs inside each projected element, mirroring `ArrayPath.leaf` for a
    `list[Model]`. An empty leaf locates the projected scalar itself
    (`dict[K, scalar]`); a non-empty leaf locates a field inside a
    `dict[K, Model]` value (or key).

    The map must be reachable without array iteration, and the leaf must be
    struct-only -- a map nested inside an array element or a container
    nested inside a map element is not representable (and
    `promote_terminal_map` / `promote_terminal_array` raise rather than
    fabricate one).
    """

    segments: tuple[StructSegment | MapSegment, ...]

    def __post_init__(self) -> None:
        map_count = sum(isinstance(s, MapSegment) for s in self.segments)
        if map_count != 1:
            raise ValueError("MapPath must contain exactly one MapSegment")
        if not all(isinstance(s, (StructSegment, MapSegment)) for s in self.segments):
            raise ValueError("MapPath segments outside the map must be struct segments")

    @property
    def _map_index(self) -> int:
        return next(i for i, s in enumerate(self.segments) if isinstance(s, MapSegment))

    @property
    def projection(self) -> MapProjection:
        seg = self.segments[self._map_index]
        assert isinstance(seg, MapSegment)
        return seg.projection

    @property
    def map_column(self) -> str:
        """Dotted name of the map column (struct prefix + map field name).

        This is what `F.col(...)` consumes; the `{key}` / `{value}` marker
        and the leaf belong to `str(path)`, not to the column reference.
        """
        return ".".join(s.name for s in self.segments[: self._map_index + 1])

    @property
    def leaf(self) -> tuple[str, ...]:
        """Names of struct segments after the `MapSegment`.

        Empty for a bare key/value projection; the field path inside each
        projected element otherwise.
        """
        return tuple(s.name for s in self.segments[self._map_index + 1 :])

    def append_struct(self, name: str) -> MapPath:
        return MapPath(segments=self.segments + (StructSegment(name=name),))

    def __str__(self) -> str:
        base = f"{self.map_column}{{{self.projection.value}}}"
        return base + "".join(f".{n}" for n in self.leaf)


FieldPath: TypeAlias = ScalarPath | ArrayPath | MapPath


# The element type of any `FieldPath.segments`, across all three variants.
# Broader than an `ArrayPath`'s `StructSegment | ArraySegment`: a `MapPath`
# adds a trailing `MapSegment`. Consumers that walk an arbitrary
# `FieldPath`'s segments -- rather than a statically known `ArrayPath` --
# annotate with this so a `MapSegment` is not a type error.
FieldSegment: TypeAlias = StructSegment | ArraySegment | MapSegment


def _segment_str(seg: StructSegment | ArraySegment) -> str:
    if isinstance(seg, ArraySegment):
        return seg.name + "[]" * seg.iter_count
    return seg.name


def _strip_map_suffix(part: str) -> MapProjection | None:
    """Return the `MapProjection` named by a trailing `{key}`/`{value}`, or None."""
    for proj in MapProjection:
        if part.endswith(f"{{{proj.value}}}"):
            return proj
    return None


def parse(encoded: str) -> FieldPath:
    """Parse a canonical encoded path like `"items[].nested.value"`.

    Trailing `[]` markers on a dotted part produce an `ArraySegment`
    with matching `iter_count`; a `{key}`/`{value}` marker produces a
    `MapSegment` (and a `MapPath`), with any dotted parts after it forming
    the map's struct leaf (e.g. `subs{value}.label`). The empty string
    returns the empty `ScalarPath`. Raises `ValueError` when any dotted
    part has an empty name (e.g. `".a"`, `"a..b"`, `"[]"`), when more than
    one map marker appears, or when an array marker combines with a map
    projection (`dict[K, list[V]]` is not representable as a `MapPath`).
    """
    if not encoded:
        return ScalarPath()
    segments: list[StructSegment | ArraySegment | MapSegment] = []
    struct_segments: list[StructSegment] = []
    has_array = False
    map_seen = False
    parts = encoded.split(".")
    for part in parts:
        projection = _strip_map_suffix(part)
        if projection is not None:
            if map_seen:
                raise ValueError(f"FieldPath has multiple map markers in {encoded!r}")
            part = part[: -(len(projection.value) + 2)]
        depth = 0
        while part.endswith("[]"):
            part = part[:-2]
            depth += 1
        if not part:
            raise ValueError(f"FieldPath part has empty name in {encoded!r}")
        if projection is not None:
            if depth > 0:
                raise ValueError(
                    f"map projection marker cannot follow array markers in {encoded!r}"
                )
            map_seen = True
            segments.append(MapSegment(name=part, projection=projection))
        elif depth > 0:
            has_array = True
            segments.append(ArraySegment(name=part, iter_count=depth))
        else:
            struct = StructSegment(name=part)
            segments.append(struct)
            struct_segments.append(struct)
    if map_seen:
        if has_array:
            raise ValueError(
                f"map projection cannot combine with array markers in {encoded!r}"
            )
        return MapPath(segments=tuple(segments))  # type: ignore[arg-type]
    if has_array:
        # No MapSegment reached this branch (map_seen is False), so the
        # tuple holds only Struct/Array segments.
        return ArrayPath(segments=tuple(segments))  # type: ignore[arg-type]
    return ScalarPath(segments=tuple(struct_segments))


def coerce(value: FieldPath | str) -> FieldPath:
    """Return *value* as a `FieldPath`, parsing it from string if needed."""
    if isinstance(value, str):
        return parse(value)
    return value


def promote_terminal_array(path: FieldPath) -> ArrayPath:
    """Promote *path*'s terminal segment to an iterated `ArraySegment`.

    A `StructSegment` terminal is *replaced* with `ArraySegment(name,
    iter_count=1)`; an `ArraySegment` terminal has its `iter_count`
    incremented. This is how a walker records entering a `list[...]`
    layer on the field it is already pointing at -- unlike `append_array`,
    which adds a new segment for a fresh nested array. Repeated calls
    build the multi-iteration terminal of a `list[list[X]]` field.

    Raises `ValueError` on an empty path: there is no terminal segment
    to promote. Raises `NotImplementedError` for a `MapPath`: a list nested
    inside a map element has no representable path, so the gap stays loud.
    """
    if not path.segments:
        raise ValueError("cannot promote the terminal of an empty path")
    if isinstance(path, MapPath):
        raise NotImplementedError("list nested inside a map element is not supported")
    *prefix, last = path.segments
    if isinstance(last, ArraySegment):
        promoted = ArraySegment(name=last.name, iter_count=last.iter_count + 1)
    else:
        promoted = ArraySegment(name=last.name, iter_count=1)
    return ArrayPath(segments=(*prefix, promoted))


def promote_terminal_map(path: FieldPath, projection: MapProjection) -> MapPath:
    """Promote *path*'s terminal struct segment to a `MapSegment`.

    Records a walker entering a `dict[K, V]` layer on the field it already
    points at, projecting to keys or values. Raises `ValueError` on an
    empty path and `NotImplementedError` when the map is reached through
    array iteration or already projects another map -- a map nested inside
    an array element or another map element has no schema field today and
    no representable `MapPath`, so the gap stays loud.
    """
    if not path.segments:
        raise ValueError("cannot promote the terminal of an empty path")
    if isinstance(path, ArrayPath):
        raise NotImplementedError("map nested under a list layer is not supported")
    if isinstance(path, MapPath):
        raise NotImplementedError("map nested inside a map element is not supported")
    *prefix, last = path.segments
    return MapPath(
        segments=(*prefix, MapSegment(name=last.name, projection=projection))  # type: ignore[arg-type]
    )
