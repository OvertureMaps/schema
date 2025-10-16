from typing import get_origin

from pydantic.json_schema import JsonDict


def subset_conflicts(a: JsonDict, b: JsonDict) -> JsonDict:
    """
    Returns conflict items that prevent `a` from being a subset of `b`.

    Parameters
    ----------
    a : JsonDict
        Candidate subset of `b`
    b : JsonDict
        Candidate supserset of `a`

    Returns
    -------
    JsonDict
        Equal to `{}` if `a` is a subset of `b`, otherwise a non-empty `dict`
        containing keys from `a` that are either missing from `b` or that have
        different values in `a` and `b`.
    """
    conflicts: JsonDict = {}
    for k, av in a.items():
        try:
            bv = b[k]
        except KeyError:
            conflicts[k] = av
            continue
        if av != bv:
            origin = get_origin(JsonDict)
            if isinstance(av, origin) and isinstance(bv, origin):
                sub_conflicts = subset_conflicts(av, bv)
                if sub_conflicts:
                    conflicts[k] = sub_conflicts
            elif isinstance(av, list | tuple) and isinstance(bv, list | tuple):
                sub_conflicts = _array_conflicts(av, bv)
                if sub_conflicts:
                    conflicts[k] = sub_conflicts
            else:
                conflicts[k] = _type_mismatch(av, bv) or _value_mismatch(av, bv)
    return conflicts


def assert_subset(a: JsonDict, b: JsonDict, a_name: str = "a", b_name: str = "b"):
    conflicts = subset_conflicts(a, b)
    if conflicts:
        raise AssertionError(
            f"expected `{a_name}` to be a subset of `{b_name}`, "
            f"but the following parts of `{a_name}` were missing or different in `{b_name}`: {conflicts} "
            f"(full context: `{a_name}` = {a}, `{b_name}` = {b})"
        )


def _type_mismatch(a: object, b: object) -> str | None:
    if type(a) is type(b):
        return None
    return f"type mismatch: {type(a).__name__} vs. {type(b).__name__} (values {repr(a)} vs. {repr(b)})"


def _value_mismatch(a: object, b: object) -> str:
    assert a != b
    return f"value mismatch: {repr(a)} vs. {repr(b)}"


def _array_conflicts(
    a: list[object] | tuple[object, ...], b: list[object] | tuple[object, ...]
) -> list[object]:
    conflicts = []
    for i, (av, bv) in enumerate(zip(a, b, strict=False)):
        origin = get_origin(JsonDict)
        if isinstance(av, origin) and isinstance(bv, origin):
            sub_conflicts = subset_conflicts(av, bv)
            if sub_conflicts:
                conflicts.append((i, sub_conflicts))
        elif av != bv:
            conflicts.append((i, _type_mismatch(av, bv) or _value_mismatch(av, bv)))

    if len(a) != len(b):
        conflicts.append(
            f"length mismatch: {len(a)} vs. {len(b)}, additional items follow"
        )
        if len(a) < len(b):
            conflicts += b[len(a) :]
        else:
            conflicts += a[len(b) :]
    return conflicts
