"""Tests for TagSelector dataclass."""

from dataclasses import FrozenInstanceError

import pytest

from overture.schema.system.discovery import TagSelector


class TestTagSelector:
    def test_default_is_empty(self) -> None:
        s = TagSelector()
        assert s.include_any == ()
        assert s.require_all == ()
        assert s.exclude_any == ()

    def test_construction_with_fields(self) -> None:
        s = TagSelector(
            include_any=("a", "b"),
            require_all=("c",),
            exclude_any=("d",),
        )
        assert s.include_any == ("a", "b")
        assert s.require_all == ("c",)
        assert s.exclude_any == ("d",)

    def test_kw_only(self) -> None:
        with pytest.raises(TypeError):
            TagSelector(("a",))  # type: ignore[misc]

    def test_frozen(self) -> None:
        s = TagSelector(include_any=("a",))
        with pytest.raises(FrozenInstanceError):
            s.include_any = ("b",)  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        a = TagSelector(include_any=("x",))
        b = TagSelector(include_any=("x",))
        assert a == b

    def test_hashable(self) -> None:
        s = TagSelector(include_any=("x",))
        d = {s: 1}
        assert d[s] == 1
