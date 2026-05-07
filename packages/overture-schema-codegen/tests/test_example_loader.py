"""Tests for examples module."""

import logging
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal

import pytest
from overture.schema.buildings.building import Building
from overture.schema.codegen.extraction.examples import (
    ExampleRecord,
    _inject_literal_fields,
    augment_missing_fields,
    flatten_model_instance,
    load_examples,
    load_examples_from_toml,
    order_example_rows,
    resolve_pyproject_path,
    validate_example,
)
from overture.schema.system.primitive import BBox, Geometry
from overture.schema.transportation import Segment
from overture.schema.transportation.segment.models import (
    RoadSegment,
    TransportationSegment,
)
from pydantic import BaseModel, ConfigDict, Field, Tag, ValidationError
from shapely.geometry import Point


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
    `project.write_pyproject()`.
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
                id = "123"

                [examples.Building.names]
                primary = "Tower"

                [examples.Building.bbox]
                xmin = 1.0
                xmax = 2.0

                [[examples.Building.sources]]
                dataset = "OSM"
                record_id = "w456"
            """)
        )

        class Names(BaseModel):
            primary: str
            secondary: str | None = None

        class Bbox(BaseModel):
            xmin: float
            xmax: float
            ymin: float | None = None
            ymax: float | None = None

        class Source(BaseModel):
            dataset: str
            record_id: str

        class MockModel(BaseModel):
            __module__ = mock_project.mod_name
            id: str
            version: int
            bbox: Bbox | None = None
            names: Names | None = None
            sources: list[Source] = []

        field_names = ["id", "bbox", "names", "sources", "version"]
        result = load_examples(MockModel, "Building", field_names)

        assert len(result) == 1
        record = result[0]
        assert isinstance(record, ExampleRecord)

        assert record.rows == [
            ("id", "123"),
            ("bbox.xmin", 1.0),
            ("bbox.xmax", 2.0),
            ("bbox.ymin", None),
            ("bbox.ymax", None),
            ("names.primary", "Tower"),
            ("names.secondary", None),
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

    def test_dict_field_kept_as_leaf(self, mock_project: MockProject) -> None:
        """Dict fields are kept as leaf values without dict_paths."""
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

        result = load_examples(MockModel, "MockModel", ["name", "tags"])

        assert len(result) == 1
        assert result[0].rows == [
            ("name", "Tower"),
            ("tags", {"color": "red", "size": "large"}),
        ]


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

    def test_valid_data_returns_instance(self) -> None:
        """Valid data returns a model instance."""

        class MockModel(BaseModel):
            name: str
            count: int

        raw = {"name": "test", "count": 42}
        result = validate_example(MockModel, raw)
        assert isinstance(result, MockModel)
        assert result.name == "test"
        assert result.count == 42

    def test_invalid_data_raises_validation_error(self) -> None:
        """Invalid data raises ValidationError."""

        class MockModel(BaseModel):
            count: int

        raw = {"count": "not_an_int"}
        with pytest.raises(ValidationError):
            validate_example(MockModel, raw)

    def test_literals_injected_before_validation(self) -> None:
        """Missing Literal fields are injected before validation."""

        class MockModel(BaseModel):
            theme: Literal["buildings"]
            name: str

        raw = {"name": "Tower"}
        result = validate_example(MockModel, raw)
        assert isinstance(result, MockModel)
        assert result.theme == "buildings"
        assert result.name == "Tower"


class _Dog(BaseModel):
    kind: Literal["dog"]
    bark: str


class _Cat(BaseModel):
    kind: Literal["cat"]
    purr: bool


_PetUnion = Annotated[
    Annotated[_Dog, Tag("dog")] | Annotated[_Cat, Tag("cat")],
    Field(discriminator="kind"),
]


class TestValidateExampleWithUnion:
    """Tests for validate_example with discriminated unions via TypeAdapter."""

    def test_validates_union_via_type_adapter(self) -> None:
        """TypeAdapter validates against a discriminated union."""
        raw = {"kind": "dog", "bark": "woof"}
        result = validate_example(_PetUnion, raw, model_fields=_Dog.model_fields)
        assert isinstance(result, _Dog)
        assert result.kind == "dog"
        assert result.bark == "woof"

    def test_invalid_union_example_raises(self) -> None:
        """Invalid data against union raises ValidationError."""
        raw = {"kind": "dog", "bark": 42}  # bark should be str
        with pytest.raises(ValidationError):
            validate_example(_PetUnion, raw, model_fields=_Dog.model_fields)

    def test_null_cross_arm_fields_stripped_for_validation(self) -> None:
        """Null fields from other union arms are stripped before validation.

        Parquet files have columns for all union arms. A road segment row
        includes rail_flags=null because the column exists. Preprocessing
        strips these so extra='forbid' models accept the data.
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
        raw = {"kind": "dog", "name": "Rex", "bark": "woof", "purr": None}
        result = validate_example(PetUnion, raw, model_fields=_Base.model_fields)
        assert isinstance(result, Dog)
        assert result.name == "Rex"
        assert result.bark == "woof"


class TestIntegration:
    """Integration tests with real schema models."""

    def test_real_building_examples_validate(self) -> None:
        """Validate real Building examples from the schema package."""
        pyproject_path = resolve_pyproject_path(Building)
        assert pyproject_path is not None, "Could not find pyproject.toml for Building"

        raw_examples = load_examples_from_toml(pyproject_path, "Building")
        assert len(raw_examples) > 0, "No Building examples found in pyproject.toml"

        for idx, raw_example in enumerate(raw_examples):
            validated = validate_example(Building, raw_example)
            assert isinstance(validated, BaseModel), (
                f"Example {idx}: Expected BaseModel"
            )

    def test_real_segment_examples_validate(self) -> None:
        """Validate real Segment examples (discriminated union with cross-arm fields)."""
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
            assert isinstance(validated, BaseModel), (
                f"Example {idx}: Expected BaseModel"
            )


class TestAugmentMissingFields:
    """Tests for augment_missing_fields function."""

    def test_no_missing_fields(self) -> None:
        """All fields present, nothing augmented."""
        rows = [("id", "123"), ("name", "test")]
        result = augment_missing_fields(rows, ["id", "name"])
        assert result == [("id", "123"), ("name", "test")]

    def test_missing_top_level_field(self) -> None:
        """Missing field added as (name, None)."""
        rows = [("id", "123")]
        result = augment_missing_fields(rows, ["id", "name", "level"])
        assert result == [("id", "123"), ("name", None), ("level", None)]

    def test_dotted_field_counts_as_present(self) -> None:
        """A dotted key like 'names.primary' counts 'names' as present."""
        rows = [("id", "123"), ("names.primary", "foo")]
        result = augment_missing_fields(rows, ["id", "names"])
        assert result == [("id", "123"), ("names.primary", "foo")]

    def test_indexed_field_counts_as_present(self) -> None:
        """A bracketed key like 'sources[0].dataset' counts 'sources' as present."""
        rows = [("id", "123"), ("sources[0].dataset", "OSM")]
        result = augment_missing_fields(rows, ["id", "sources"])
        assert result == [("id", "123"), ("sources[0].dataset", "OSM")]

    def test_union_cross_arm_fields_added(self) -> None:
        """Fields from other union arms are added as None."""
        rows = [
            ("kind", "dog"),
            ("name", "Rex"),
            ("bark", "woof"),
        ]
        field_names = ["kind", "name", "bark", "purr"]
        result = augment_missing_fields(rows, field_names)
        assert result == [
            ("kind", "dog"),
            ("name", "Rex"),
            ("bark", "woof"),
            ("purr", None),
        ]


class TestFlattenModelInstance:
    """Tests for flatten_model_instance function."""

    def test_simple_fields(self) -> None:
        """Flatten simple model fields."""

        class Simple(BaseModel):
            id: str
            version: int

        instance = Simple(id="123", version=1)
        result = flatten_model_instance(instance)
        assert result == [("id", "123"), ("version", 1)]

    def test_nested_model(self) -> None:
        """Nested BaseModel fields use dot notation."""

        class Inner(BaseModel):
            primary: str
            secondary: str | None = None

        class Outer(BaseModel):
            name: str
            names: Inner

        instance = Outer(name="test", names=Inner(primary="foo"))
        result = flatten_model_instance(instance)
        assert result == [
            ("name", "test"),
            ("names.primary", "foo"),
            ("names.secondary", None),
        ]

    def test_list_of_models(self) -> None:
        """List of BaseModel uses bracket notation."""

        class Source(BaseModel):
            dataset: str
            record_id: str

        class Feature(BaseModel):
            id: str
            sources: list[Source]

        instance = Feature(
            id="123",
            sources=[
                Source(dataset="OSM", record_id="w123"),
                Source(dataset="MSFT", record_id="w456"),
            ],
        )
        result = flatten_model_instance(instance)
        assert result == [
            ("id", "123"),
            ("sources[0].dataset", "OSM"),
            ("sources[0].record_id", "w123"),
            ("sources[1].dataset", "MSFT"),
            ("sources[1].record_id", "w456"),
        ]

    def test_dict_field_kept_as_leaf(self) -> None:
        """Dict-typed fields are leaf values, not recursed."""

        class Tagged(BaseModel):
            name: str
            tags: dict[str, str]

        instance = Tagged(name="test", tags={"color": "red", "size": "large"})
        result = flatten_model_instance(instance)
        assert result == [
            ("name", "test"),
            ("tags", {"color": "red", "size": "large"}),
        ]

    def test_none_defaulted_fields_appear(self) -> None:
        """Fields with None defaults still appear in output."""

        class WithDefaults(BaseModel):
            name: str
            level: int | None = None
            height: float | None = None

        instance = WithDefaults(name="test")
        result = flatten_model_instance(instance)
        assert result == [
            ("name", "test"),
            ("level", None),
            ("height", None),
        ]

    def test_plain_list_kept_as_leaf(self) -> None:
        """Plain list of primitives is a single leaf value."""

        class WithList(BaseModel):
            phones: list[str]

        instance = WithList(phones=["+1234", "+5678"])
        result = flatten_model_instance(instance)
        assert result == [("phones", ["+1234", "+5678"])]

    def test_empty_list_kept_as_leaf(self) -> None:
        """Empty list is a leaf value."""

        class WithList(BaseModel):
            tags: list[str] = []

        instance = WithList()
        result = flatten_model_instance(instance)
        assert result == [("tags", [])]

    def test_nested_list_of_lists_of_models(self) -> None:
        """list[list[Model]] uses double-index notation."""

        class Node(BaseModel):
            division_id: str
            name: str

        class Feature(BaseModel):
            hierarchies: list[list[Node]]

        instance = Feature(
            hierarchies=[
                [
                    Node(division_id="aaa", name="Country"),
                    Node(division_id="bbb", name="Region"),
                ],
            ]
        )
        result = flatten_model_instance(instance)
        assert result == [
            ("hierarchies[0][0].division_id", "aaa"),
            ("hierarchies[0][0].name", "Country"),
            ("hierarchies[0][1].division_id", "bbb"),
            ("hierarchies[0][1].name", "Region"),
        ]

    def test_none_model_field_is_leaf(self) -> None:
        """A model-typed field with None value is a leaf, not recursed."""

        class Inner(BaseModel):
            value: str

        class Outer(BaseModel):
            name: str
            inner: Inner | None = None

        instance = Outer(name="test")
        result = flatten_model_instance(instance)
        assert result == [("name", "test"), ("inner", None)]

    def test_field_alias(self) -> None:
        """Field with validation_alias uses the alias as key."""

        class Aliased(BaseModel):
            class_: Literal["building"] = Field(validation_alias="class")
            name: str

        instance = Aliased.model_validate({"class": "building", "name": "Tower"})
        result = flatten_model_instance(instance)
        assert result == [("class", "building"), ("name", "Tower")]

    def test_slots_based_field_flattened(self) -> None:
        """Non-BaseModel types with __slots__ and properties are flattened."""

        class WithBBox(BaseModel):
            id: str
            bbox: BBox | None = None

        instance = WithBBox(id="123", bbox=BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4.0))
        result = flatten_model_instance(instance)
        assert result == [
            ("id", "123"),
            ("bbox.xmin", 1.0),
            ("bbox.ymin", 2.0),
            ("bbox.xmax", 3.0),
            ("bbox.ymax", 4.0),
        ]

    def test_none_slots_based_field_is_leaf(self) -> None:
        """A slots-based field with None value is a leaf."""

        class WithBBox(BaseModel):
            id: str
            bbox: BBox | None = None

        instance = WithBBox(id="123")
        result = flatten_model_instance(instance)
        assert result == [("id", "123"), ("bbox", None)]

    def test_single_slot_wrapper_is_leaf(self) -> None:
        """Single-slot types (wrappers like Geometry) are leaf values."""

        class WithGeom(BaseModel):
            id: str
            geometry: Geometry

        geom = Geometry(Point(1, 2))
        instance = WithGeom(id="123", geometry=geom)
        result = flatten_model_instance(instance)
        assert result == [("id", "123"), ("geometry", geom)]
