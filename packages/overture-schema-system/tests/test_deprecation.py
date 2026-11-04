"""
Deprecation belongs to the class that declares it.

PEP 702's `@deprecated` sets `__deprecated__` on the class it decorates and warns when that class
is instantiated or subclassed. A subclass is not itself deprecated: instantiating it does not warn.
A model-constraint decorator returns a new subclass of the class it decorates. When it is applied over
`@deprecated`, the returned class is the one the module exports, so it must declare the deprecation
itself, and its own subclassing must not raise PEP 702's subclass warning.
"""

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from typing_extensions import deprecated

from overture.schema.system.create_model import create_model
from overture.schema.system.json_schema import json_schema
from overture.schema.system.model_constraint import no_extra_fields, require_any_of

MESSAGE = "Use `NewModel` instead."


@contextmanager
def recorded_warnings() -> Iterator[list[warnings.WarningMessage]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def deprecation_warnings(caught: list[warnings.WarningMessage]) -> list[str]:
    return [
        str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)
    ]


class TestDecoratorOverDeprecated:
    def test_no_warning_at_definition(self) -> None:
        with recorded_warnings() as caught:

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str

        assert deprecation_warnings(caught) == []

    def test_declares_deprecation(self) -> None:
        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str

        assert OldModel.__dict__.get("__deprecated__") == MESSAGE

    def test_warns_on_instantiate_and_validate(self) -> None:
        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str

        with pytest.warns(DeprecationWarning, match="NewModel"):
            OldModel(name="x")
        with pytest.warns(DeprecationWarning, match="NewModel"):
            OldModel.model_validate({"name": "x"})

    def test_keeps_category(self) -> None:
        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE, category=FutureWarning)
            class OldModel(BaseModel):
                name: str

        with pytest.warns(FutureWarning, match="NewModel"):
            OldModel(name="x")

    def test_constraint_still_applies(self) -> None:
        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str

            with pytest.raises(ValidationError):
                OldModel.model_validate({"name": "x", "extra": 1})

    def test_json_schema_marks_deprecated(self) -> None:
        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str

        assert json_schema(OldModel).get("deprecated") is True


class TestSubclassingDecoratorsOverDeprecated:
    """Subclassing warns once, however many decorators sit over `@deprecated`.

    Each layer the decorators derive would otherwise add its own warning, and removing those layers'
    warnings must not drop an `__init_subclass__` the chain declares.
    """

    def test_warns_once(self) -> None:
        with recorded_warnings():

            @require_any_of("name", "alias")
            @no_extra_fields
            @deprecated(MESSAGE, category=FutureWarning)
            class OldModel(BaseModel):
                name: str | None = None
                alias: str | None = None

        with recorded_warnings() as caught:

            class NewModel(OldModel):
                pass

        assert [(w.category, str(w.message)) for w in caught] == [
            (FutureWarning, MESSAGE)
        ]

    def test_runs_the_deprecated_model_own_init_subclass(self) -> None:
        subclassed: list[str] = []
        with recorded_warnings():

            @require_any_of("name", "alias")
            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(BaseModel):
                name: str | None = None
                alias: str | None = None

                def __init_subclass__(cls, **kwargs: Any) -> None:
                    super().__init_subclass__(**kwargs)
                    subclassed.append(cls.__name__)

        subclassed.clear()
        with recorded_warnings() as caught:

            class NewModel(OldModel):
                pass

        assert subclassed == ["NewModel"]
        assert deprecation_warnings(caught) == [MESSAGE]

    def test_runs_an_inherited_init_subclass(self) -> None:
        subclassed: list[str] = []

        class Base(BaseModel):
            def __init_subclass__(cls, **kwargs: Any) -> None:
                super().__init_subclass__(**kwargs)
                subclassed.append(cls.__name__)

        with recorded_warnings():

            @no_extra_fields
            @deprecated(MESSAGE)
            class OldModel(Base):
                name: str

        subclassed.clear()
        with recorded_warnings() as caught:

            class NewModel(OldModel):
                pass

        assert subclassed == ["NewModel"]
        assert deprecation_warnings(caught) == [MESSAGE]

    def test_keeps_an_init_subclass_the_derived_model_declares(self) -> None:
        subclassed: list[str] = []

        def record(cls: type, **kwargs: object) -> None:
            subclassed.append(cls.__name__)

        @deprecated(MESSAGE)
        class OldModel(BaseModel):
            name: str

        Derived = create_model(
            "Derived",
            __base__=OldModel,
            __validators__={"__init_subclass__": classmethod(record)},  # type: ignore[dict-item]
        )
        subclassed.clear()
        with recorded_warnings() as caught:

            class NewModel(Derived):  # type: ignore[valid-type,misc]
                pass

        assert subclassed == ["NewModel"]
        assert deprecation_warnings(caught) == [MESSAGE]


class TestDeprecatedOverDecorator:
    """The control: `@deprecated` outermost already behaves, and must keep doing so."""

    def test_no_warning_at_definition_and_warns_on_instantiate(self) -> None:
        with recorded_warnings() as caught:

            @deprecated(MESSAGE)
            @no_extra_fields
            class OldModel(BaseModel):
                name: str

        assert deprecation_warnings(caught) == []
        with pytest.warns(DeprecationWarning, match="NewModel"):
            OldModel(name="x")
        assert json_schema(OldModel).get("deprecated") is True
