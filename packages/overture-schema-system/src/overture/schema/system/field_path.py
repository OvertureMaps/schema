"""Structural representation of a field path through a nested schema.

A `FieldPath` is one of two variants:

- `ScalarPath` -- a sequence of `StructSegment` values locating a value
  that requires no iteration to reach.
- `ArrayPath` -- a sequence of `StructSegment` and `ArraySegment` values,
  with at least one `ArraySegment`, locating a value reached by iterating
  one or more arrays. Each `ArraySegment` carries `iter_count`, the number
  of `[]` markers on its name in the canonical encoding (multi-depth
  segments encode nested-list iteration without an intervening struct,
  e.g. `list[list[X]]` parses as a single `ArraySegment` with
  `iter_count=2`).

The canonical string form (`str(path)`) round-trips through `parse`.
Code that needs to emit a path into source or labels calls `str(path)`
at the boundary; everything else operates on segments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

__all__ = [
    "ArrayPath",
    "ArraySegment",
    "FieldPath",
    "PathSegment",
    "ScalarPath",
    "StructSegment",
    "coerce",
    "parse",
    "promote_terminal_array",
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


PathSegment: TypeAlias = StructSegment | ArraySegment


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

    segments: tuple[PathSegment, ...]

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
          mismatched struct prefix, etc.). Callers must apply the gate
          at column level instead.

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
        target_first_array_name = self.segments[n_prefix].name
        gate_boundary = gate_segs[n_prefix]
        if not isinstance(gate_boundary, ArraySegment):
            return None
        if gate_boundary.name != target_first_array_name:
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


FieldPath: TypeAlias = ScalarPath | ArrayPath


def _segment_str(seg: PathSegment) -> str:
    if isinstance(seg, ArraySegment):
        return seg.name + "[]" * seg.iter_count
    return seg.name


def parse(encoded: str) -> FieldPath:
    """Parse a canonical encoded path like `"items[].nested.value"`.

    Trailing `[]` markers on a dotted part produce an `ArraySegment`
    with matching `iter_count`. The empty string returns the empty
    `ScalarPath`. Raises `ValueError` when any dotted part has an empty
    name (e.g. `".a"`, `"a..b"`, `"[]"`).
    """
    if not encoded:
        return ScalarPath()
    segments: list[PathSegment] = []
    struct_segments: list[StructSegment] = []
    has_array = False
    for part in encoded.split("."):
        depth = 0
        while part.endswith("[]"):
            part = part[:-2]
            depth += 1
        if not part:
            raise ValueError(f"FieldPath part has empty name in {encoded!r}")
        if depth > 0:
            has_array = True
            segments.append(ArraySegment(name=part, iter_count=depth))
        else:
            struct = StructSegment(name=part)
            segments.append(struct)
            struct_segments.append(struct)
    if has_array:
        return ArrayPath(segments=tuple(segments))
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
    to promote.
    """
    if not path.segments:
        raise ValueError("cannot promote the terminal of an empty path")
    *prefix, last = path.segments
    if isinstance(last, ArraySegment):
        promoted = ArraySegment(name=last.name, iter_count=last.iter_count + 1)
    else:
        promoted = ArraySegment(name=last.name, iter_count=1)
    return ArrayPath(segments=(*prefix, promoted))
