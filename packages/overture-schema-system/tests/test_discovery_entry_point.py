"""Tests for entry-point string utilities."""

from pathlib import PurePosixPath

import pytest

from overture.schema.system.discovery.entry_point import (
    entry_point_class_alias,
    entry_point_to_path,
    resolve_entry_point_key,
)


class TestEntryPointToPath:
    def test_typical_overture_entry_point(self) -> None:
        path, cls = entry_point_to_path("overture.schema.places:Place")
        assert path == PurePosixPath("overture/schema/places")
        assert cls == "Place"

    def test_single_segment_module(self) -> None:
        path, cls = entry_point_to_path("myschema:Foo")
        assert path == PurePosixPath("myschema")
        assert cls == "Foo"

    def test_deeply_nested_module(self) -> None:
        path, cls = entry_point_to_path("a.b.c.d.e:Thing")
        assert path == PurePosixPath("a/b/c/d/e")
        assert cls == "Thing"

    def test_missing_colon_raises(self) -> None:
        with pytest.raises(ValueError, match="module:Class"):
            entry_point_to_path("overture.schema.places.Place")

    def test_class_name_with_dot_kept(self) -> None:
        # Class name after the colon is taken verbatim — Python class
        # names can't contain dots, but we don't validate.
        path, cls = entry_point_to_path("a.b:Outer.Inner")
        assert path == PurePosixPath("a/b")
        assert cls == "Outer.Inner"


class TestEntryPointClassAlias:
    def test_returns_snake_case_class_name(self) -> None:
        assert entry_point_class_alias("overture.schema.places:Place") == "place"

    def test_handles_pascal_case_class(self) -> None:
        assert (
            entry_point_class_alias("overture.schema.buildings:BuildingPart")
            == "building_part"
        )

    def test_handles_acronyms(self) -> None:
        assert (
            entry_point_class_alias("overture.schema.places:HTMLParser")
            == "html_parser"
        )

    def test_bare_name_is_snake_cased(self) -> None:
        # Tolerant of registry keys that aren't entry-point-formatted —
        # the snake-case form of the whole string is returned.
        assert entry_point_class_alias("BareName") == "bare_name"


class TestResolveEntryPointKey:
    def test_exact_match(self) -> None:
        registry = {"overture.schema.places:Place": object()}
        assert (
            resolve_entry_point_key("overture.schema.places:Place", registry)
            == "overture.schema.places:Place"
        )

    def test_snake_case_alias_match(self) -> None:
        registry = {"overture.schema.places:Place": object()}
        assert (
            resolve_entry_point_key("place", registry) == "overture.schema.places:Place"
        )

    def test_ambiguous_lists_candidates(self) -> None:
        registry = {
            "overture.schema.places:Place": object(),
            "annex.schema.places:Place": object(),
        }
        with pytest.raises(ValueError, match="ambiguous"):
            resolve_entry_point_key("place", registry)

    def test_unknown_lists_known(self) -> None:
        registry = {"overture.schema.places:Place": object()}
        with pytest.raises(ValueError, match="Unknown"):
            resolve_entry_point_key("zzz", registry)

    def test_acronym_class_name_resolves(self) -> None:
        registry = {
            "ns.a:HTMLParser": object(),
            "ns.b:HTMLParser": object(),
        }
        with pytest.raises(ValueError, match=r"ns\.a:HTMLParser"):
            resolve_entry_point_key("html_parser", registry)
