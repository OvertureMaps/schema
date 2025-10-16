from typing import cast


def subset_conflicts(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    """
    Returns conflict items that prevent `a` from being a subset of `b`.

    Parameters
    ----------
    a : dict[str, object]
        Candidate subset of `b`
    b : dict[str, object]
        Candidate supserset of `a`

    Returns
    -------
    dict[str, object]
        Equal to `{}` if `a` is a subset of `b`, otherwise a non-empty `dict`
        containing keys from `a` that are either missing from `b` or that have
        different values in `a` and `b`.
    """
    conflicts: dict[str, object] = {}
    for k, av in a.items():
        try:
            bv = b[k]
        except KeyError:
            conflicts[k] = av
            continue
        if av != bv:
            if isinstance(av, dict) and isinstance(bv, dict):
                dict_conflicts = subset_conflicts(cast(dict, av), cast(dict, bv))
                if dict_conflicts:
                    conflicts[k] = dict_conflicts
            elif isinstance(av, list | tuple) and isinstance(bv, list | tuple):
                array_conflicts = _array_conflicts(
                    cast(list[object] | tuple[object, ...], av),
                    cast(list[object] | tuple[object, ...], bv),
                )
                if array_conflicts:
                    conflicts[k] = array_conflicts
            else:
                conflicts[k] = _type_mismatch(av, bv) or _value_mismatch(av, bv)
    return conflicts


def assert_subset(
    a: dict[str, object], b: dict[str, object], a_name: str = "a", b_name: str = "b"
) -> None:
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
    conflicts: list[object] = []
    for i, (av, bv) in enumerate(zip(a, b, strict=False)):
        if isinstance(av, dict) and isinstance(bv, dict):
            sub_conflicts = subset_conflicts(
                cast(dict[str, object], av), cast(dict[str, object], bv)
            )
            if sub_conflicts:
                conflicts.append(
                    {
                        "index": i,
                        "conflict": sub_conflicts,
                    }
                )
        elif av != bv:
            conflicts.append(
                {
                    "index": i,
                    "conflict": _type_mismatch(av, bv) or _value_mismatch(av, bv),
                }
            )

    if len(a) != len(b):
        conflicts.append(
            f"length mismatch: {len(a)} vs. {len(b)}, additional items follow"
        )
        if len(a) < len(b):
            conflicts += b[len(a) :]
        else:
            conflicts += a[len(b) :]
    return conflicts
