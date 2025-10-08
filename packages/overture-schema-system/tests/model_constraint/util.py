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
            else:
                conflicts[k] = av


def assert_subset(a: JsonDict, b: JsonDict, a_name: str = "a", b_name: str = "b"):
    conflicts = subset_conflicts(a, b)
    if conflicts:
        raise AssertionError(
            f"expected `{a_name}` to be a subset of `{b_name}`, \
                but the following parts of `{a_name}` were missing or different in `{b_name}`: {conflicts} \
                (full context: `{a_name}` = {a}, `{b_name}` = {b})"
        )
