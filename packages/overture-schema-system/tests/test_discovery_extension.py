"""Tests for extension handling in the discovery pipeline (no entry points required)."""

import logging
from collections.abc import Iterable
from typing import Annotated, Literal, cast

import pytest
from pydantic import BaseModel, Field, Tag, TypeAdapter

from overture.schema.system.discovery import discovery as discovery_module
from overture.schema.system.discovery.discovery import _generate_tags, extend_models
from overture.schema.system.discovery.keys import ModelKey, TagProviderKey
from overture.schema.system.discovery.tag_providers import extension_provider
from overture.schema.system.discovery.types import ModelDict
from overture.schema.system.extension import extends, wrap_extension
from overture.schema.system.typing_util import collect_types


class Target(BaseModel):
    name: str


class Unrelated(BaseModel):
    value: int


class RoadSeg(BaseModel):
    kind: Literal["road"] = "road"


class RailSeg(BaseModel):
    kind: Literal["rail"] = "rail"


# A discriminated-union alias entry point, like the transportation theme's `Segment`.
SegmentAlias = Annotated[
    Annotated[RoadSeg, Tag("road")] | Annotated[RailSeg, Tag("rail")],
    Field(discriminator="kind"),
]


@extends(Target)
class Ext(BaseModel):
    note: str


def _key(name: str, *tags: str) -> ModelKey:
    return ModelKey(name=name, entry_point=f"m:{name}", tags=frozenset(tags))


def _model(value: object) -> type[BaseModel]:
    assert isinstance(value, type) and issubclass(value, BaseModel)
    return value


def test_extend_models_merges_into_targets() -> None:
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None
    models: ModelDict = {
        _key("ext", "extension"): wrapper,
        _key("target", "feature"): Target,
        _key("unrelated"): Unrelated,
    }
    result = extend_models(models)

    by_name = {key.name: model for key, model in result.items()}
    # Extension entry is left untouched.
    assert by_name["ext"] is wrapper
    # Target gains the field; unrelated model is unchanged.
    assert "ext" in _model(by_name["target"]).model_fields
    assert by_name["unrelated"] is Unrelated


def test_extend_models_noop_without_extensions() -> None:
    models: ModelDict = {_key("target", "feature"): Target}
    assert extend_models(models) is models


def test_extend_models_extends_model_sharing_an_extension_name() -> None:
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None
    # A plain model registered under the same entry-point name as the extension
    # (the keys differ by entry_point, so both coexist) must still be extended.
    models: ModelDict = {
        _key("ext", "extension"): wrapper,
        ModelKey(name="ext", entry_point="other:Target", tags=frozenset()): Target,
    }
    result = extend_models(models)

    by_entry_point = {key.entry_point: model for key, model in result.items()}
    assert by_entry_point["m:ext"] is wrapper
    assert "ext" in _model(by_entry_point["other:Target"]).model_fields


def test_extend_models_skips_duplicate_field_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @extends(Target)
    class OtherExt(BaseModel):
        other: int

    first = wrap_extension("ext", Ext)
    second = wrap_extension("ext", OtherExt)
    assert first is not None and second is not None
    first_key = ModelKey(
        name="ext", entry_point="first:Ext", tags=frozenset({"extension"})
    )
    second_key = ModelKey(
        name="ext", entry_point="second:OtherExt", tags=frozenset({"extension"})
    )
    target_key = _key("target")

    with caplog.at_level(logging.WARNING):
        result = extend_models(
            {first_key: first, second_key: second, target_key: Target}
        )

    assert result[target_key] is Target
    assert "Multiple extensions are registered for field 'ext'" in caplog.text


def test_extend_models_isolates_per_model_failures(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None

    real = discovery_module.create_extended_model

    def failing(model: object, extensions: object) -> object:
        if model is Unrelated:
            raise RuntimeError("boom")
        return real(model, extensions)  # type: ignore[arg-type]

    monkeypatch.setattr(discovery_module, "create_extended_model", failing)
    models: ModelDict = {
        _key("ext", "extension"): wrapper,
        _key("target"): Target,
        _key("unrelated"): Unrelated,
    }
    with caplog.at_level(logging.WARNING):
        result = extend_models(models)

    by_name = {key.name: model for key, model in result.items()}
    # One model failing must not abort the pass: the target is still extended and
    # the failing model is kept, unextended, instead of being dropped.
    assert "ext" in _model(by_name["target"]).model_fields
    assert by_name["unrelated"] is Unrelated
    assert "Could not apply extensions to model 'unrelated'" in caplog.text


def test_extend_models_warns_when_extension_matches_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None
    # Ext targets Target, which is absent from the registry -- the extension would
    # otherwise be silently ignored.
    models: ModelDict = {
        _key("ext", "extension"): wrapper,
        _key("unrelated"): Unrelated,
    }
    with caplog.at_level(logging.WARNING):
        result = extend_models(models)

    assert result[_key("unrelated")] is Unrelated
    assert "Extension 'ext' was not applied to any discovered model" in caplog.text


def test_extend_models_extends_arms_of_rootmodel_entry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from pydantic import RootModel

    class SegmentRoot(
        RootModel[Annotated[RoadSeg | RailSeg, Field(discriminator="kind")]]
    ):
        pass

    @extends(RoadSeg)
    class SegExt(BaseModel):
        note: str

    wrapper = wrap_extension("seg_ext", SegExt)
    assert wrapper is not None
    models: ModelDict = {
        _key("seg_ext", "extension"): wrapper,
        _key("segment", "feature"): SegmentRoot,
    }
    with caplog.at_level(logging.WARNING):
        result = extend_models(models)

    by_name = {key.name: model for key, model in result.items()}
    rebuilt = by_name["segment"]
    assert isinstance(rebuilt, type) and issubclass(rebuilt, SegmentRoot)
    # Discriminator survives the rebuild and the targeted arm takes extension data.
    assert rebuilt.model_fields["root"].discriminator == "kind"
    v = rebuilt.model_validate({"kind": "road", "seg_ext": {"note": "hi"}})
    assert v.model_dump()["seg_ext"]["note"] == "hi"
    # The application site is inside the root -- no spurious "not applied" warning.
    assert "was not applied to any discovered model" not in caplog.text


def test_extend_models_contains_self_referential_rootmodel_entry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from pydantic import RootModel

    class Loop(RootModel):  # type: ignore[type-arg]
        root: "Loop | Target"

    Loop.model_rebuild()

    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None
    models: ModelDict = {
        _key("ext", "extension"): wrapper,
        _key("loop"): Loop,
        _key("target"): Target,
    }
    with caplog.at_level(logging.WARNING):
        result = extend_models(models)

    by_name = {key.name: model for key, model in result.items()}
    # The self-referential entry is kept unextended with a warning; the rest of the
    # pass -- including the warning aggregation -- is unaffected.
    assert by_name["loop"] is Loop
    assert "Could not apply extensions to model 'loop'" in caplog.text
    assert "ext" in _model(by_name["target"]).model_fields
    assert "was not applied to any discovered model" not in caplog.text


def test_extension_provider_tags_wrapper() -> None:
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None
    tags = extension_provider([wrapper], _key("ext"), set())
    assert "extension" in tags


def test_extension_provider_ignores_plain_models() -> None:
    tags = extension_provider([Target], _key("target"), set())
    assert "extension" not in tags


def test_generate_tags_passes_only_models_for_union_alias_entry() -> None:
    received: list[list[type[BaseModel]]] = []

    def provider(
        models: Iterable[type[BaseModel]], key: ModelKey, tags: set[str]
    ) -> list[str]:
        received.append(list(models))
        return []

    provider_key = TagProviderKey(
        name="probe", entry_point="m:probe", package_name="overture-schema-system"
    )
    _generate_tags(SegmentAlias, _key("segment"), {provider_key: provider})

    (models,) = received
    assert set(models) == {RoadSeg, RailSeg}
    assert all(isinstance(m, type) and issubclass(m, BaseModel) for m in models)


def test_extend_models_extends_every_arm_of_union_alias_target() -> None:
    @extends(SegmentAlias)
    class SegExt(BaseModel):
        note: str

    wrapper = wrap_extension("seg_ext", SegExt)
    assert wrapper is not None
    # The alias entry is not a class, so it needs a cast into ModelDict's value
    # type -- discovery stores union aliases verbatim at runtime.
    models = cast(
        ModelDict,
        {
            _key("seg_ext", "extension"): wrapper,
            _key("segment", "feature"): SegmentAlias,
        },
    )
    result = extend_models(models)

    by_name = {key.name: model for key, model in result.items()}
    extended_alias = by_name["segment"]
    # Every arm of the alias gains the extension field.
    arms = [
        tp
        for tp in collect_types(extended_alias)
        if isinstance(tp, type) and issubclass(tp, BaseModel)
    ]
    assert arms
    assert all("seg_ext" in model.model_fields for model in arms)
    # The discriminated-union structure survives the rebuild.
    road = TypeAdapter(extended_alias).validate_python({"kind": "road"})
    assert isinstance(road, RoadSeg)


def test_tags_are_generated_from_the_extended_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tags must describe the classes `discover_models` actually returns.

    A provider inspecting model fields sees extension-contributed fields,
    which requires tag generation to run after extension application.
    """
    wrapper = wrap_extension("ext", Ext)
    assert wrapper is not None

    class _Entry:
        def __init__(self, name: str, value: object) -> None:
            self.name = name
            self.value = f"m:{name}"
            self._loaded = value

        def load(self) -> object:
            return self._loaded

    def fake_entry_points(*, group: str) -> list[_Entry]:
        if group == "overture.models":
            return [_Entry("target", Target), _Entry("ext", Ext)]
        return []

    def field_provider(
        types: Iterable[type[BaseModel]], key: ModelKey, tags: set[str]
    ) -> set[str]:
        return {
            f"has:{field}"
            for cls in types
            for field in cls.model_fields
            if field == "ext"
        }

    monkeypatch.setattr(
        discovery_module.importlib.metadata, "entry_points", fake_entry_points
    )
    monkeypatch.setattr(
        discovery_module,
        "discover_tag_providers",
        lambda: {
            TagProviderKey(
                name="fields", entry_point="t:fields", package_name="test"
            ): field_provider
        },
    )
    models = discovery_module.discover_models()
    target_key = next(k for k in models if k.name == "target")
    assert "has:ext" in target_key.tags
    assert "ext" in models[target_key].model_fields
