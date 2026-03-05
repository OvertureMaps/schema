"""Tests for example_loader module."""

import logging
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal

import pytest
from overture.schema.codegen.extraction.examples import (
    ExampleRecord,
    _denull,
    _inject_literal_fields,
    collect_dict_paths,
    flatten_example,
    load_examples,
    load_examples_from_toml,
    order_example_rows,
    resolve_pyproject_path,
    validate_example,
)
from overture.schema.codegen.extraction.specs import FieldSpec, ModelSpec
from overture.schema.codegen.extraction.type_analyzer import TypeInfo, TypeKind
from pydantic import BaseModel, ConfigDict, Field, Tag, ValidationError


class TestFlattenExample:
    """Tests for flatten_example function."""

    def test_simple_fields(self) -> None:
        """Flatten simple key-value pairs."""
        raw = {"id": "123", "version": 1, "name": "test"}
        result = flatten_example(raw)
        assert result == [("id", "123"), ("version", 1), ("name", "test")]

    def test_nested_dict(self) -> None:
        """Flatten nested dict to dot notation."""
        raw = {"names": {"primary": "foo", "common": {"en": "bar"}}}
        result = flatten_example(raw)
        assert result == [
            ("names.primary", "foo"),
            ("names.common.en", "bar"),
        ]

    def test_list_of_dicts(self) -> None:
        """Flatten list of dicts with array notation."""
        raw = {"sources": [{"dataset": "OSM", "record_id": "w123"}]}
        result = flatten_example(raw)
        assert result == [
            ("sources[0].dataset", "OSM"),
            ("sources[0].record_id", "w123"),
        ]

    def test_bbox_flattened_at_top_level(self) -> None:
        """Bbox fields are flattened like any other nested dict."""
        raw = {
            "id": "123",
            "bbox": {"xmin": -176.6, "xmax": -176.64},
            "version": 1,
        }
        result = flatten_example(raw)
        assert result == [
            ("id", "123"),
            ("bbox.xmin", -176.6),
            ("bbox.xmax", -176.64),
            ("version", 1),
        ]

    def test_plain_list_kept_as_value(self) -> None:
        """Plain lists (non-dict items) are kept as values."""
        raw = {"phones": ["+1234", "+5678"]}
        result = flatten_example(raw)
        assert result == [("phones", ["+1234", "+5678"])]

    def test_empty_dict(self) -> None:
        """Empty dict produces empty list."""
        raw: dict[str, object] = {}
        result = flatten_example(raw)
        assert result == []

    def test_empty_list(self) -> None:
        """Empty list is kept as value."""
        raw: dict[str, object] = {"tags": []}
        result = flatten_example(raw)
        assert result == [("tags", [])]

    def test_list_of_list_of_dicts(self) -> None:
        """Flatten list[list[dict]] with double-index notation."""
        raw = {
            "hierarchies": [
                [
                    {"division_id": "aaa", "name": "Country"},
                    {"division_id": "bbb", "name": "Region"},
                ],
            ]
        }
        result = flatten_example(raw)
        assert result == [
            ("hierarchies[0][0].division_id", "aaa"),
            ("hierarchies[0][0].name", "Country"),
            ("hierarchies[0][1].division_id", "bbb"),
            ("hierarchies[0][1].name", "Region"),
        ]

    def test_multiple_list_items(self) -> None:
        """Handle multiple items in list of dicts."""
        raw = {
            "sources": [
                {"dataset": "OSM", "confidence": 0.9},
                {"dataset": "MSFT", "confidence": 0.8},
            ]
        }
        result = flatten_example(raw)
        assert result == [
            ("sources[0].dataset", "OSM"),
            ("sources[0].confidence", 0.9),
            ("sources[1].dataset", "MSFT"),
            ("sources[1].confidence", 0.8),
        ]

    def test_dict_field_kept_as_leaf(self) -> None:
        """Dict values at dict_paths are kept as leaf values."""
        raw = {
            "name": "test",
            "tags": {"color": "red", "size": "large"},
        }
        result = flatten_example(raw, dict_paths=frozenset({"tags"}))
        assert result == [
            ("name", "test"),
            ("tags", {"color": "red", "size": "large"}),
        ]

    def test_nested_dict_path_kept_as_leaf(self) -> None:
        """Dict values at nested dict_paths are kept as leaf values."""
        raw = {
            "names": {
                "primary": "Tower",
                "common": {"en": "Tower", "fr": "Tour"},
            },
        }
        result = flatten_example(raw, dict_paths=frozenset({"names.common"}))
        assert result == [
            ("names.primary", "Tower"),
            ("names.common", {"en": "Tower", "fr": "Tour"}),
        ]

    def test_empty_dict_paths_preserves_behavior(self) -> None:
        """Empty dict_paths (default) recurses all dicts as before."""
        raw = {"tags": {"color": "red"}}
        result = flatten_example(raw)
        assert result == [("tags.color", "red")]

    def test_dict_inside_list_kept_as_leaf(self) -> None:
        """Dict at indexed path matches schema path in dict_paths."""
        raw = {
            "items": [
                {"name": "a", "tags": {"color": "red"}},
                {"name": "b", "tags": {"size": "large"}},
            ],
        }
        result = flatten_example(raw, dict_paths=frozenset({"items[].tags"}))
        assert result == [
            ("items[0].name", "a"),
            ("items[0].tags", {"color": "red"}),
            ("items[1].name", "b"),
            ("items[1].tags", {"size": "large"}),
        ]


class TestOrderExampleRows:
    """Tests for order_example_rows function."""

    def test_order_by_field_names(self) -> None:
        """Order rows by position in field_names."""
        flat_rows = [("version", 1), ("id", "123"), ("name", "test")]
        field_names = ["id", "name", "version"]
        result = order_example_rows(flat_rows, field_names)
        assert result == [("id", "123"), ("name", "test"), ("version", 1)]

    def test_extract_base_field_from_dot_notation(self) -> None:
        """Extract base field from dotted keys."""
        flat_rows = [
            ("names.primary", "foo"),
            ("id", "123"),
            ("names.common.en", "bar"),
        ]
        field_names = ["id", "names"]
        result = order_example_rows(flat_rows, field_names)
        assert result == [
            ("id", "123"),
            ("names.primary", "foo"),
            ("names.common.en", "bar"),
        ]

    def test_extract_base_field_from_array_notation(self) -> None:
        """Extract base field from array notation."""
        flat_rows = [
            ("sources[0].dataset", "OSM"),
            ("id", "123"),
            ("sources[0].record_id", "w123"),
            ("sources[1].dataset", "MSFT"),
        ]
        field_names = ["id", "sources"]
        result = order_example_rows(flat_rows, field_names)
        assert result == [
            ("id", "123"),
            ("sources[0].dataset", "OSM"),
            ("sources[0].record_id", "w123"),
            ("sources[1].dataset", "MSFT"),
        ]

    def test_order_with_mixed_notation(self) -> None:
        """Order rows with mixed simple, dotted, and array notation."""
        flat_rows = [
            ("version", 1),
            ("sources[0].dataset", "OSM"),
            ("id", "123"),
            ("names.primary", "foo"),
        ]
        field_names = ["id", "names", "sources", "version"]
        result = order_example_rows(flat_rows, field_names)
        assert result == [
            ("id", "123"),
            ("names.primary", "foo"),
            ("sources[0].dataset", "OSM"),
            ("version", 1),
        ]

    def test_unknown_fields_sort_to_end(self) -> None:
        """Unknown fields sort to end, maintaining relative order."""
        flat_rows = [
            ("unknown2", "b"),
            ("id", "123"),
            ("unknown1", "a"),
            ("version", 1),
        ]
        field_names = ["id", "version"]
        result = order_example_rows(flat_rows, field_names)
        assert result == [
            ("id", "123"),
            ("version", 1),
            ("unknown2", "b"),
            ("unknown1", "a"),
        ]


class TestLoadExamplesFromToml:
    """Tests for load_examples_from_toml function."""

    def test_load_example_list(self, tmp_path: Path) -> None:
        """Load examples for a model from TOML."""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            dedent("""
                [project]
                name = "test-package"

                [[examples.Building]]
                id = "123"
                version = 1

                [[examples.Building]]
                id = "456"
                version = 2
            """)
        )

        result = load_examples_from_toml(toml_path, "Building")
        assert len(result) == 2
        assert result[0] == {"id": "123", "version": 1}
        assert result[1] == {"id": "456", "version": 2}

    def test_model_not_found_returns_empty(self, tmp_path: Path) -> None:
        """Return empty list when model has no examples."""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            dedent("""
                [project]
                name = "test-package"

                [[examples.Building]]
                id = "123"
            """)
        )

        result = load_examples_from_toml(toml_path, "Road")
        assert result == []

    def test_no_examples_section_returns_empty(self, tmp_path: Path) -> None:
        """Return empty list when no examples section exists."""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            dedent("""
                [project]
                name = "test-package"
            """)
        )

        result = load_examples_from_toml(toml_path, "Building")
        assert result == []


class MockProject:
    """A temporary project directory with registered mock modules."""

    def __init__(self, root: Path, pyproject: Path, mod_name: str) -> None:
        self.root = root
        self.pyproject = pyproject
        self.mod_name = mod_name
        self._registered_modules: list[str] = [mod_name]

    def write_pyproject(self, content: str) -> None:
        self.pyproject.write_text(content)

    def add_submodule(self, *subdirs: str) -> str:
        """Register a deeper module under this project's src directory.

        Returns the module name for use in __module__ attributes.
        """
        pkg_dir = self.root / "src" / Path(*subdirs)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        module_file = pkg_dir / "module.py"
        module_file.write_text("# module")

        sub_mod_name = f"{self.mod_name}_{'_'.join(subdirs)}"
        mod = types.ModuleType(sub_mod_name)
        mod.__file__ = str(module_file)
        sys.modules[sub_mod_name] = mod
        self._registered_modules.append(sub_mod_name)
        return sub_mod_name

    def cleanup(self) -> None:
        for name in self._registered_modules:
            sys.modules.pop(name, None)


@pytest.fixture
def mock_project(tmp_path: Path) -> Iterator[MockProject]:
    """Create a project directory with a mock module registered in sys.modules.

    Yields a MockProject with root, pyproject path, and mod_name.
    Writes a minimal pyproject.toml by default; tests can overwrite via
    ``project.write_pyproject()``.
    """
    root = tmp_path / "project"
    root.mkdir()
    pyproject = root / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'")

    src_dir = root / "src"
    src_dir.mkdir()
    module_file = src_dir / "module.py"
    module_file.write_text("# module")

    mod_name = f"_test_mock_{id(tmp_path)}"
    mod = types.ModuleType(mod_name)
    mod.__file__ = str(module_file)
    sys.modules[mod_name] = mod

    project = MockProject(root=root, pyproject=pyproject, mod_name=mod_name)
    yield project
    project.cleanup()


class TestResolvePyprojectPath:
    """Tests for resolve_pyproject_path function."""

    def test_finds_pyproject_in_parent_dirs(self, mock_project: MockProject) -> None:
        """Walk up from module location to find pyproject.toml."""
        deeper_mod = mock_project.add_submodule("pkg")

        class MockModel:
            __module__ = deeper_mod

        result = resolve_pyproject_path(MockModel)
        assert result == mock_project.pyproject

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Return None when pyproject.toml doesn't exist."""
        module_dir = tmp_path / "src"
        module_dir.mkdir()
        module_file = module_dir / "module.py"
        module_file.write_text("# module")

        mod_name = f"_test_resolve_nf_{id(tmp_path)}"
        mod = types.ModuleType(mod_name)
        mod.__file__ = str(module_file)
        sys.modules[mod_name] = mod
        try:

            class MockModel:
                __module__ = mod_name

            result = resolve_pyproject_path(MockModel)
            assert result is None
        finally:
            sys.modules.pop(mod_name, None)

    def test_returns_none_when_no_module(self) -> None:
        """Return None when model's module is not in sys.modules."""

        class MockModel:
            __module__ = "_nonexistent_module_for_test"

        result = resolve_pyproject_path(MockModel)
        assert result is None


class TestLoadExamples:
    """Tests for load_examples entry point."""

    def test_end_to_end(self, mock_project: MockProject) -> None:
        """Load, flatten, and order examples end-to-end."""
        mock_project.write_pyproject(
            dedent("""
                [project]
                name = "test"

                [[examples.Building]]
                version = 1
                names = { primary = "Tower" }
                id = "123"

                [examples.Building.bbox]
                xmin = 1.0
                xmax = 2.0

                [[examples.Building.sources]]
                dataset = "OSM"
                record_id = "w456"
            """)
        )

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name
            id: str
            version: int
            names: dict[str, object]
            sources: list[dict[str, object]]

        field_names = ["id", "bbox", "names", "sources", "version"]
        result = load_examples(MockModel, "Building", field_names)

        assert len(result) == 1
        record = result[0]
        assert isinstance(record, ExampleRecord)

        assert record.rows == [
            ("id", "123"),
            ("bbox.xmin", 1.0),
            ("bbox.xmax", 2.0),
            ("names.primary", "Tower"),
            ("sources[0].dataset", "OSM"),
            ("sources[0].record_id", "w456"),
            ("version", 1),
        ]

    def test_returns_empty_on_missing_pyproject(self) -> None:
        """Return empty list when model's module not in sys.modules."""

        class MockModel(BaseModel):
            __module__ = "_nonexistent_module_for_load_test"

        result = load_examples(MockModel, "Building", ["id"])
        assert result == []

    def test_returns_empty_on_missing_model(self, mock_project: MockProject) -> None:
        """Return empty list when model has no examples."""

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name

        result = load_examples(MockModel, "Building", ["id"])
        assert result == []

    def test_invalid_examples_skipped_with_warning(
        self, mock_project: MockProject, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Invalid examples are skipped and warning logged."""
        mock_project.write_pyproject(
            dedent("""
                [project]
                name = "test"

                [[examples.MockModel]]
                name = "valid"
                count = 1

                [[examples.MockModel]]
                name = "invalid"
                count = "not_an_int"

                [[examples.MockModel]]
                name = "also_valid"
                count = 2
            """)
        )

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name
            name: str
            count: int

        caplog.set_level(logging.WARNING)

        result = load_examples(MockModel, "MockModel", ["name", "count"])

        assert len(result) == 2
        assert result[0].rows == [("name", "valid"), ("count", 1)]
        assert result[1].rows == [("name", "also_valid"), ("count", 2)]

        assert any(
            "MockModel" in record.message
            and "validation" in record.message.lower()
            and str(mock_project.pyproject) in record.message
            for record in caplog.records
        )

    def test_dict_paths_keep_dicts_as_leaves(self, mock_project: MockProject) -> None:
        """Dict fields listed in dict_paths stay as leaf values."""
        mock_project.write_pyproject(
            dedent("""
                [project]
                name = "test"

                [[examples.MockModel]]
                name = "Tower"

                [examples.MockModel.tags]
                color = "red"
                size = "large"
            """)
        )

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name
            name: str
            tags: dict[str, str]

        result = load_examples(
            MockModel,
            "MockModel",
            ["name", "tags"],
            dict_paths=frozenset({"tags"}),
        )

        assert len(result) == 1
        assert result[0].rows == [
            ("name", "Tower"),
            ("tags", {"color": "red", "size": "large"}),
        ]

    def test_denulled_values_in_output(self, mock_project: MockProject) -> None:
        """Flattened output contains None not "null" strings."""
        mock_project.write_pyproject(
            dedent("""
                [project]
                name = "test"

                [[examples.MockModel]]
                name = "test"
                value = "null"
            """)
        )

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name
            name: str
            value: int | None

        result = load_examples(MockModel, "MockModel", ["name", "value"])

        assert len(result) == 1
        assert result[0].rows == [("name", "test"), ("value", None)]


class TestDenull:
    """Tests for _denull function."""

    def test_converts_null_string_to_none(self) -> None:
        """Top-level "null" strings become None."""
        assert _denull({"a": "null"}) == {"a": None}

    def test_nested_dict(self) -> None:
        """Recurse into nested dicts."""
        data = {"a": {"b": "null"}}
        assert _denull(data) == {"a": {"b": None}}

    def test_list_of_dicts(self) -> None:
        """Recurse into dicts inside lists."""
        data = {"items": [{"x": "null"}]}
        assert _denull(data) == {"items": [{"x": None}]}

    def test_mixed_types_unchanged(self) -> None:
        """Non-"null" strings, ints, bools, and plain lists pass through."""
        data = {
            "name": "hello",
            "count": 42,
            "flag": True,
            "tags": ["a", "b"],
            "score": 3.14,
        }
        assert _denull(data) == data

    def test_no_mutation(self) -> None:
        """Original dict is not modified."""
        original = {"a": "null", "b": {"c": "null"}}
        _denull(original)
        assert original == {"a": "null", "b": {"c": "null"}}

    def test_empty_dict(self) -> None:
        """Empty dict returns empty dict."""
        assert _denull({}) == {}

    def test_deeply_nested(self) -> None:
        """Handle multiple levels of nesting."""
        data = {"a": {"b": {"c": "null"}}}
        assert _denull(data) == {"a": {"b": {"c": None}}}

    def test_null_strings_in_plain_list(self) -> None:
        """Convert "null" strings inside plain lists."""
        data = {"tags": ["a", "null", "b"]}
        assert _denull(data) == {"tags": ["a", None, "b"]}


class TestInjectLiteralFields:
    """Tests for _inject_literal_fields function."""

    def test_injects_single_value_literal(self) -> None:
        """Inject field with single-value Literal annotation."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower", "theme": "buildings"}

    def test_skips_non_literal_field(self) -> None:
        """Do not inject fields without Literal annotations."""

        class MockModel(BaseModel):
            name: str
            count: int

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower"}

    def test_skips_already_present_field(self) -> None:
        """Do not overwrite fields already in data."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            name: str

        data = {"theme": "custom", "name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"theme": "custom", "name": "Tower"}

    def test_respects_validation_alias(self) -> None:
        """Use validation_alias when injecting."""

        class MockModel(BaseModel):
            class_: Literal["building"] = Field(validation_alias="class")
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower", "class": "building"}

    def test_no_mutation(self) -> None:
        """Original data dict is not modified."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            name: str

        data = {"name": "Tower"}
        original_data = data.copy()
        _inject_literal_fields(MockModel.model_fields, data)
        assert data == original_data

    def test_multiple_literal_fields(self) -> None:
        """Inject multiple Literal fields."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            type: Literal["building"]
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower", "theme": "buildings", "type": "building"}

    def test_skips_multi_value_literal(self) -> None:
        """Do not inject Literal with multiple values."""

        class MockModel(BaseModel):
            status: Literal["active", "inactive"]
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower"}

    def test_respects_alias_fallback(self) -> None:
        """Fall back to alias if validation_alias not set."""

        class MockModel(BaseModel):
            class_: Literal["building"] = Field(alias="class")
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower", "class": "building"}

    def test_unwraps_optional_literal(self) -> None:
        """Inject Optional[Literal["x"]] fields (union-wrapped by Pydantic)."""

        class MockModel(BaseModel):
            theme: Literal["buildings"] | None = None
            name: str

        data = {"name": "Tower"}
        result = _inject_literal_fields(MockModel.model_fields, data)
        assert result == {"name": "Tower", "theme": "buildings"}


class TestValidateExample:
    """Tests for validate_example function."""

    def test_valid_data_passes(self) -> None:
        """Valid data is validated and denulled dict returned."""

        class MockModel(BaseModel):
            name: str
            count: int

        raw = {"name": "test", "count": 42}
        result = validate_example(MockModel, raw)
        assert result == {"name": "test", "count": 42}

    def test_invalid_data_raises_validation_error(self) -> None:
        """Invalid data raises ValidationError."""

        class MockModel(BaseModel):
            count: int

        raw = {"count": "not_an_int"}
        with pytest.raises(ValidationError):
            validate_example(MockModel, raw)

    def test_denulled_dict_returned(self) -> None:
        """Denulled dict is returned, not raw or preprocessed."""

        class MockModel(BaseModel):
            name: str
            value: int | None

        raw = {"name": "test", "value": "null"}
        result = validate_example(MockModel, raw)
        assert result == {"name": "test", "value": None}

    def test_literals_injected_before_validation(self) -> None:
        """Missing Literal fields are injected before validation."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            name: str

        raw = {"name": "Tower"}
        result = validate_example(MockModel, raw)
        # Returned dict is denulled, NOT preprocessed (no injected literals)
        assert result == {"name": "Tower"}


class TestValidateExampleWithUnion:
    """Tests for validate_example with discriminated unions via TypeAdapter."""

    def test_validates_union_via_type_adapter(self) -> None:
        """TypeAdapter validates against a discriminated union."""

        class Dog(BaseModel):
            kind: Literal["dog"]
            bark: str

        class Cat(BaseModel):
            kind: Literal["cat"]
            purr: bool

        PetUnion = Annotated[
            Annotated[Dog, Tag("dog")] | Annotated[Cat, Tag("cat")],
            Field(discriminator="kind"),
        ]

        raw = {"kind": "dog", "bark": "woof"}
        result = validate_example(PetUnion, raw, model_fields=Dog.model_fields)
        assert result == {"kind": "dog", "bark": "woof"}

    def test_invalid_union_example_raises(self) -> None:
        """Invalid data against union raises ValidationError."""

        class Dog(BaseModel):
            kind: Literal["dog"]
            bark: str

        class Cat(BaseModel):
            kind: Literal["cat"]
            purr: bool

        PetUnion = Annotated[
            Annotated[Dog, Tag("dog")] | Annotated[Cat, Tag("cat")],
            Field(discriminator="kind"),
        ]

        raw = {"kind": "dog", "bark": 42}  # bark should be str
        with pytest.raises(ValidationError):
            validate_example(PetUnion, raw, model_fields=Dog.model_fields)

    def test_null_cross_arm_fields_accepted(self) -> None:
        """Null fields from other union arms are accepted in flat-schema examples.

        Parquet files have columns for all union arms. A road segment row
        includes ``rail_flags=null`` because the column exists in the table.
        Validation should accept these cross-arm nulls.
        """

        class _Base(BaseModel):
            model_config = ConfigDict(extra="forbid")
            kind: str
            name: str

        class Dog(_Base):
            kind: Literal["dog"]
            bark: str | None = None

        class Cat(_Base):
            kind: Literal["cat"]
            purr: bool | None = None

        PetUnion = Annotated[
            Annotated[Dog, Tag("dog")] | Annotated[Cat, Tag("cat")],
            Field(discriminator="kind"),
        ]

        # Flat schema: Dog example includes Cat's "purr" field as null
        raw = {"kind": "dog", "name": "Rex", "bark": "woof", "purr": "null"}
        result = validate_example(PetUnion, raw, model_fields=_Base.model_fields)
        # Returned dict preserves the original denulled data
        assert result == {
            "kind": "dog",
            "name": "Rex",
            "bark": "woof",
            "purr": None,
        }


class TestIntegration:
    """Integration tests with real schema models."""

    def test_real_building_examples_validate(self) -> None:
        """Validate real Building examples from the schema package."""
        pytest.importorskip("overture.schema.buildings.building")

        from overture.schema.buildings.building import Building  # noqa: PLC0415

        # Find the pyproject.toml for the Building model
        pyproject_path = resolve_pyproject_path(Building)
        assert pyproject_path is not None, "Could not find pyproject.toml for Building"

        # Load raw examples from TOML
        raw_examples = load_examples_from_toml(pyproject_path, "Building")
        assert len(raw_examples) > 0, "No Building examples found in pyproject.toml"

        # Validate each example
        for idx, raw_example in enumerate(raw_examples):
            # Should not raise ValidationError
            validated = validate_example(Building, raw_example)
            assert isinstance(validated, dict), f"Example {idx}: Expected dict result"

    def test_real_segment_examples_validate(self) -> None:
        """Validate real Segment examples (discriminated union with cross-arm fields)."""
        pytest.importorskip("overture.schema.transportation")

        from overture.schema.transportation import Segment  # noqa: PLC0415
        from overture.schema.transportation.segment.models import (  # noqa: PLC0415
            RoadSegment,
            TransportationSegment,
        )

        pyproject_path = resolve_pyproject_path(RoadSegment)
        assert pyproject_path is not None

        raw_examples = load_examples_from_toml(pyproject_path, "Segment")
        assert len(raw_examples) > 0, "No Segment examples found"

        for idx, raw_example in enumerate(raw_examples):
            validated = validate_example(
                Segment,
                raw_example,
                model_fields=TransportationSegment.model_fields,
            )
            assert isinstance(validated, dict), f"Example {idx}: Expected dict result"


def _field(
    name: str,
    *,
    kind: TypeKind = TypeKind.PRIMITIVE,
    base_type: str = "str",
    is_dict: bool = False,
    list_depth: int = 0,
    is_required: bool = True,
    model: ModelSpec | None = None,
    starts_cycle: bool = False,
) -> FieldSpec:
    """Build a FieldSpec with sensible defaults for testing."""
    return FieldSpec(
        name=name,
        type_info=TypeInfo(
            base_type=base_type, kind=kind, is_dict=is_dict, list_depth=list_depth
        ),
        description=None,
        is_required=is_required,
        model=model,
        starts_cycle=starts_cycle,
    )


class TestCollectDictPaths:
    """Tests for collect_dict_paths."""

    def test_no_dict_fields(self) -> None:
        """Model with only primitive fields returns empty set."""
        fields = [_field("name")]
        assert collect_dict_paths(fields) == frozenset()

    def test_top_level_dict_field(self) -> None:
        """Dict field at top level is collected."""
        fields = [
            _field("name"),
            _field("tags", is_dict=True, is_required=False),
        ]
        assert collect_dict_paths(fields) == frozenset({"tags"})

    def test_nested_dict_in_sub_model(self) -> None:
        """Dict field inside a sub-model produces dotted path."""
        inner_fields = [
            _field("primary"),
            _field("common", is_dict=True, is_required=False),
        ]
        inner_model = ModelSpec(name="Names", description=None, fields=inner_fields)
        fields = [
            _field("names", kind=TypeKind.MODEL, base_type="Names", model=inner_model)
        ]
        assert collect_dict_paths(fields) == frozenset({"names.common"})

    def test_list_of_model_with_dict(self) -> None:
        """Dict inside list-of-model uses [] in path."""
        inner_fields = [_field("tags", is_dict=True, is_required=False)]
        inner_model = ModelSpec(name="Item", description=None, fields=inner_fields)
        fields = [
            _field(
                "items",
                kind=TypeKind.MODEL,
                base_type="Item",
                list_depth=1,
                model=inner_model,
            ),
        ]
        assert collect_dict_paths(fields) == frozenset({"items[].tags"})

    def test_nested_list_depth(self) -> None:
        """list[list[Model]] produces [][] in path."""
        inner_fields = [_field("tags", is_dict=True)]
        inner_model = ModelSpec(name="Item", description=None, fields=inner_fields)
        fields = [
            _field(
                "items",
                kind=TypeKind.MODEL,
                base_type="Item",
                list_depth=2,
                model=inner_model,
            ),
        ]
        assert collect_dict_paths(fields) == frozenset({"items[][].tags"})

    def test_cycle_stops_recursion(self) -> None:
        """Fields with starts_cycle=True are not recursed into."""
        inner_fields = [_field("data", is_dict=True, is_required=False)]
        inner_model = ModelSpec(name="Node", description=None, fields=inner_fields)
        fields = [
            _field(
                "child",
                kind=TypeKind.MODEL,
                base_type="Node",
                is_required=False,
                model=inner_model,
                starts_cycle=True,
            ),
        ]
        assert collect_dict_paths(fields) == frozenset()
