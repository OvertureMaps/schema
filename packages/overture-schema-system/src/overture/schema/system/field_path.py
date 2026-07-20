"""Structural representation of a field path through a nested schema.

A `FieldPath` is one of two variants:

- `Direct` -- a sequence of `StructSegment` values locating a value that
  requires no iteration to reach.
- `Iterated` -- a sequence of `StructSegment`, `ArraySegment`, and
  `MapSegment` values with at least one iterating (`Array`/`Map`) segment,
  locating a value reached by iterating one or more arrays or maps. Each
  iterating segment is exactly one iteration frame. A container nested
  directly inside another container with no field name between (e.g.
  `list[list[X]]`, `dict[K, list[X]]`) is an *anonymous* iterating segment
  -- an `ArraySegment` or `MapSegment` whose `name` is empty, meaning "the
  parent element is itself this container." Anonymity is read through
  `is_anonymous`, never `name == ""` directly.

Examples map a Pydantic field annotation to the canonical string form of
a check on its innermost value:

    x: int                              -> "x"                (Direct)
    parent: Parent (field `value`)      -> "parent.value"     (Direct)
    items: list[Item] (field `v`)       -> "items[].v"        (Iterated)
    tags: dict[str, str] (values)       -> "tags{value}"      (Iterated)
    tags: dict[str, str] (keys)         -> "tags{key}"        (Iterated)
    grid: list[list[int]]               -> "grid[][]"         (Iterated)
    subs: dict[str, list[X]] (values)   -> "subs{value}[]"    (Iterated)
    items: list[dict[str, X]] (values)  -> "items[]{value}"   (Iterated)

In the multi-container forms the first marker is a *named* segment (it
carries the field name) and each trailing marker is *anonymous* -- the
parent element is itself the next container, so no field name separates
them. The canonical string (`str(path)`) round-trips through `parse`;
the `[]` / `{key}` / `{value}` sugar is unchanged, so existing encodings
round-trip and only the internal segment list generalizes. Code that
emits a path into source or labels calls `str(path)` at that boundary;
everything else operates on segments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

__all__ = [
    "ArraySegment",
    "Direct",
    "FieldPath",
    "FieldSegment",
    "Iterated",
    "MapProjection",
    "MapSegment",
    "StructSegment",
    "coerce",
    "parse",
    "promote_terminal",
    "terminal_run_start",
]


@dataclass(frozen=True, slots=True)
class StructSegment:
    """A struct field navigation step."""

    name: str


@dataclass(frozen=True, slots=True)
class ArraySegment:
    """An array column entered with one level of iteration.

    An empty `name` marks an *anonymous* segment: the parent element is
    itself a list (`list[list[...]]`), iterated once more with no field
    navigation. Read anonymity via `is_anonymous`, never `name == ""`.
    """

    name: str = ""

    @property
    def is_anonymous(self) -> bool:
        """Whether this segment is a nameless extra iteration of the prior container."""
        return self.name == ""


class MapProjection(Enum):
    """Which side of a `dict[K, V]` a `MapSegment` iterates."""

    KEY = "key"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class MapSegment:
    """A map column entered by projecting to its keys or values.

    `projection` selects keys or values; the projected side is iterated
    like an array, so checks on a `MapSegment` render through the same
    element machinery as `ArraySegment`. An empty `name` marks an
    *anonymous* segment: the parent element is itself a map
    (`dict[K, dict[K2, V]]`, `list[dict]`), projected once more with no
    field navigation. Read anonymity via `is_anonymous`, never `name == ""`.
    """

    name: str
    projection: MapProjection

    @property
    def is_anonymous(self) -> bool:
        """Whether this segment is a nameless extra projection of the prior container."""
        return self.name == ""


# The element type of any `FieldPath.segments`. A `Direct` holds only
# `StructSegment`s; an `Iterated` mixes all three.
FieldSegment: TypeAlias = StructSegment | ArraySegment | MapSegment


def _is_iterating(seg: FieldSegment) -> bool:
    """Whether *seg* is an iterating (`Array`/`Map`) segment."""
    return isinstance(seg, (ArraySegment, MapSegment))


def _first_iterating(segments: tuple[FieldSegment, ...]) -> ArraySegment | MapSegment:
    """Return the first iterating segment (Array/Map) in *segments*.

    Callers guarantee at least one exists (the `Iterated` invariant).
    """
    for seg in segments:
        if isinstance(seg, (ArraySegment, MapSegment)):
            return seg
    raise AssertionError("no iterating segment; caller violated the invariant")


@dataclass(frozen=True, slots=True)
class Direct:
    """Locate a non-iterated value in a row."""

    segments: tuple[StructSegment, ...] = ()

    def append_struct(self, name: str) -> Direct:
        """Return a new `Direct` with *name* appended as a struct segment."""
        return Direct(segments=self.segments + (StructSegment(name=name),))

    def append_array(self, name: str) -> Iterated:
        """Return an `Iterated` with *name* appended as a named array segment."""
        return Iterated(segments=self.segments + (ArraySegment(name=name),))

    def __str__(self) -> str:
        return ".".join(s.name for s in self.segments)


@dataclass(frozen=True, slots=True)
class Iterated:
    """Locate an iterated value; iteration structure is part of the location.

    Segments mix `StructSegment`, `ArraySegment`, and `MapSegment`.
    Invariants (enforced in `__post_init__`): at least one iterating
    (`Array`/`Map`) segment, and the first iterating segment is named
    (anonymity only ever follows another iterating segment). A struct
    prefix before the first iterating segment is allowed (e.g.
    `parent.items[].value`).
    """

    segments: tuple[FieldSegment, ...]

    def __post_init__(self) -> None:
        if not any(_is_iterating(s) for s in self.segments):
            raise ValueError("Iterated must contain at least one Array/Map segment")
        if _first_iterating(self.segments).is_anonymous:
            raise ValueError("first iterating segment must be named, not anonymous")

    def append_struct(self, name: str) -> Iterated:
        """Return a new `Iterated` with *name* appended to the struct leaf."""
        return Iterated(segments=self.segments + (StructSegment(name=name),))

    def append_array(self, name: str) -> Iterated:
        """Return a new `Iterated` with *name* appended as a named array segment."""
        return Iterated(segments=self.segments + (ArraySegment(name=name),))

    @property
    def outer_column(self) -> str:
        """Dotted name of the outermost iterated column.

        The struct prefix plus the first iterating segment's name
        (unbracketed, unprojected). This is what `F.col(...)`,
        `array_check("...", ...)`, or `map_values_check("...", ...)`
        consumes.
        """
        names: list[str] = []
        for seg in self.segments:
            names.append(seg.name)
            if _is_iterating(seg):
                break
        return ".".join(names)

    @property
    def column_prefix(self) -> Direct:
        """Struct segments before the first iterating segment.

        Returns an empty `Direct(())` when an iterating segment is first.
        """
        prefix: list[StructSegment] = []
        for seg in self.segments:
            if _is_iterating(seg):
                break
            assert isinstance(seg, StructSegment)
            prefix.append(seg)
        return Direct(segments=tuple(prefix))

    @property
    def leaf(self) -> tuple[str, ...]:
        """Names of struct segments after the last iterating segment."""
        last_iter = max(i for i, s in enumerate(self.segments) if _is_iterating(s))
        return tuple(s.name for s in self.segments[last_iter + 1 :])

    @property
    def iter_frames(
        self,
    ) -> tuple[tuple[tuple[str, ...], ArraySegment | MapSegment], ...]:
        """One frame per *named* iterating segment.

        Each entry is `(prefix_structs, segment)` where `prefix_structs` is
        the sequence of struct segment names between the previous named
        iterating segment (or the start of the path) and this one. An
        anonymous iterating segment does not start a new frame -- it is an
        extra iteration folded into the preceding named frame, surfaced
        separately by `iter_struct_paths`. Carrying the segment lets
        downstream pick the runtime helper and read `projection`.
        """
        frames: list[tuple[tuple[str, ...], ArraySegment | MapSegment]] = []
        prefix: list[str] = []
        for seg in self.segments:
            if isinstance(seg, (ArraySegment, MapSegment)):
                if not seg.is_anonymous:
                    frames.append((tuple(prefix), seg))
                prefix = []
            else:
                prefix.append(seg.name)
        return tuple(frames)

    @property
    def iter_struct_paths(self) -> tuple[tuple[str, ...], ...]:
        """Per non-outermost iteration: the struct path that reaches its container.

        For each named iterating segment past the first, emit `(prefix_structs
        + segment_name)` -- the navigation FROM the previous iteration's
        element TO this container. For each anonymous iterating segment, emit
        `()` -- the parent element is already the next container, so there is
        no navigation.

        Returns an empty tuple when the path iterates only once.
        """
        paths: list[tuple[str, ...]] = []
        prefix: list[str] = []
        first = True
        for seg in self.segments:
            if isinstance(seg, (ArraySegment, MapSegment)):
                if first:
                    first = False
                elif seg.is_anonymous:
                    paths.append(())
                else:
                    paths.append((*prefix, seg.name))
                prefix = []
            else:
                prefix.append(seg.name)
        return tuple(paths)

    def element_relative_gate(self, gate: FieldPath) -> tuple[str, ...] | None:
        """Path inside this array's element scope that names *gate*.

        **Precondition (stated loudly):** valid only when the first iterating
        segment is an `ArraySegment`; guaranteed because `check_builder`
        zeros the nullable gate whenever it enters any iterated container, so
        a map-first path never carries a gate. The `assert` below on the
        boundary segment makes the precondition a hard failure if violated.

        Three return states:

        - `tuple[str, ...]` (non-empty) -- "reachable with descent":
          `gate` enters the same outer array as this path and names a
          struct descendant inside its element. The returned segments
          name that descendant relative to the element.
        - `()` -- "reachable, no descent": `gate` is the outer array
          itself; the element variable IS the gated value.
        - `None` -- "not reachable": `gate` does not cross into this
          path's element scope (different outer array, scalar gate,
          mismatched struct prefix, mismatched boundary iteration depth,
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
        if not isinstance(gate, Iterated):
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
        target_run = _array_run_length(self.segments, n_prefix)
        gate_run = _array_run_length(gate_segs, n_prefix)
        if gate_run != target_run:
            return None
        inner_segments = gate_segs[n_prefix + gate_run :]
        for seg in inner_segments:
            if not isinstance(seg, StructSegment):
                raise NotImplementedError(
                    f"gate path contains a nested array segment past the "
                    f"element boundary (gate={gate!r}, self={self!r})"
                )
        return tuple(s.name for s in inner_segments)

    def __str__(self) -> str:
        parts: list[str] = []
        for seg in self.segments:
            token = _segment_str(seg)
            if isinstance(seg, (ArraySegment, MapSegment)) and seg.is_anonymous:
                parts[-1] += token
            else:
                parts.append(token)
        return ".".join(parts)


FieldPath: TypeAlias = Direct | Iterated


def _segment_str(seg: FieldSegment) -> str:
    if isinstance(seg, ArraySegment):
        return "[]" if seg.is_anonymous else seg.name + "[]"
    if isinstance(seg, MapSegment):
        marker = f"{{{seg.projection.value}}}"
        return marker if seg.is_anonymous else seg.name + marker
    return seg.name


def _array_run_length(segments: tuple[FieldSegment, ...], start: int) -> int:
    """Count the ArraySegment run starting at *start*.

    The run is the named segment at `segments[start]` (which must be an
    `ArraySegment`) plus any immediately-following anonymous ArraySegments
    -- the total iteration depth of a multi-bracket terminal like
    `hierarchies[][]`.
    """
    length = 1
    idx = start + 1
    while idx < len(segments):
        candidate = segments[idx]
        if not (isinstance(candidate, ArraySegment) and candidate.is_anonymous):
            break
        length += 1
        idx += 1
    return length


def terminal_run_start(segments: tuple[FieldSegment, ...]) -> int:
    """Return the index where the trailing bracket run's named segment sits.

    Scans backward from the last segment while it is an anonymous
    `ArraySegment`, stopping at the first segment that isn't (or at index
    0). The result names the run's *named* segment -- e.g. the first of
    the two segments behind a multi-bracket terminal like
    `hierarchies[][]` -- or simply the last segment when the path doesn't
    end in a bracket run at all.

    The `Iterated` invariant (the first iterating segment is always named)
    guarantees the scan never needs to pass index 0. The mirror of
    `_array_run_length`, which counts the same run forward from this index:
    `_array_run_length(segments, terminal_run_start(segments))` gives the
    run's length whenever the terminal segment is an `ArraySegment`.
    """
    index = len(segments) - 1
    while index > 0:
        candidate = segments[index]
        if not (isinstance(candidate, ArraySegment) and candidate.is_anonymous):
            break
        index -= 1
    return index


_MARKER = re.compile(r"\[\]|\{(key|value)\}")


def parse(encoded: str) -> FieldPath:
    """Parse a canonical encoded path like `"items[].nested.value"`.

    A left-to-right marker tokenizer. Splits on `.`; for each dotted part,
    reads the `name` up to the first marker (`[` or `{`), then scans markers
    (`[]`, `{key}`, `{value}`) left to right against the remainder. A part
    with no marker becomes a `StructSegment`. The first marker on a part
    becomes a *named* container segment on `name`; each subsequent marker
    becomes an *anonymous* container segment (its parent element is itself a
    container). Because anonymous segments attach to the previous token,
    every `.`-delimited part begins with a name.

    Examples: `hierarchies[][]` -> two `ArraySegment`s (named, anonymous);
    `subs{value}[]` -> `MapSegment` then anonymous `ArraySegment`;
    `items[]{value}` -> `ArraySegment` then anonymous `MapSegment`;
    `subs{value}.label` -> `MapSegment` then `StructSegment` leaf. The empty
    string returns the empty `Direct`. Raises `ValueError` when any dotted
    part has an empty name (e.g. `".a"`, `"a..b"`, `"[]"`, `"a.{key}"`).
    """
    if not encoded:
        return Direct()
    segments: list[FieldSegment] = []
    has_iter = False
    for part in encoded.split("."):
        m = _MARKER.search(part)
        name = part if m is None else part[: m.start()]
        if not name:
            raise ValueError(f"FieldPath part has empty name in {encoded!r}")
        if m is None:
            segments.append(StructSegment(name=name))
            continue
        has_iter = True
        first = True
        for mk in _MARKER.finditer(part):
            seg_name = name if first else ""
            if mk.group() == "[]":
                segments.append(ArraySegment(name=seg_name))
            else:
                segments.append(
                    MapSegment(name=seg_name, projection=MapProjection(mk.group(1)))
                )
            first = False
    if has_iter:
        return Iterated(segments=tuple(segments))
    return Direct(segments=tuple(segments))  # type: ignore[arg-type]


def coerce(value: FieldPath | str) -> FieldPath:
    """Return *value* as a `FieldPath`, parsing it from string if needed."""
    if isinstance(value, str):
        return parse(value)
    return value


def promote_terminal(
    path: FieldPath, *, projection: MapProjection | None = None
) -> Iterated:
    """Promote *path*'s terminal into an iterating segment.

    Records a walker entering a container (`list[...]` when *projection* is
    `None`, `dict[K, V]` when set) on the field it already points at:

    - a `StructSegment` terminal is *replaced* with a *named* container
      segment taking the struct's name;
    - an iterating terminal has an *anonymous* container segment *appended*
      (the parent element is itself a container).

    Every nesting a walker can enter -- struct into a list or map, and a
    container directly inside another container -- is representable this way,
    so the promotion always succeeds. Raises `ValueError` on an empty path:
    there is no terminal segment to promote.
    """
    if not path.segments:
        raise ValueError("cannot promote the terminal of an empty path")
    *prefix, last = path.segments
    named = last.name if isinstance(last, StructSegment) else ""
    new: ArraySegment | MapSegment = (
        ArraySegment(name=named)
        if projection is None
        else MapSegment(name=named, projection=projection)
    )
    if isinstance(last, StructSegment):
        return Iterated(segments=(*prefix, new))
    return Iterated(segments=(*path.segments, new))
