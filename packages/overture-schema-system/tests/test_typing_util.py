from typing import Annotated, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Field, RootModel
from pydantic.fields import FieldInfo

from overture.schema.system.typing_util import denoted_type


class _Arm(BaseModel):
    pass


class _ArmA(_Arm):
    type: Literal["a"]


class _ArmB(_Arm):
    type: Literal["b"]


_Arms = Annotated[_ArmA | _ArmB, Field(discriminator="type")]


class _NamedArms(RootModel[_Arms]):
    """A discriminated union given a name."""


class _RenamedArms(RootModel[_NamedArms]):
    """A RootModel over another RootModel."""


class _SelfReferentialRoot(RootModel[int]):
    """A RootModel rewired to be its own root, to exercise the cycle guard.

    A statically recursive base crashes mypy, so the self-reference is
    installed after the class exists.
    """


_SelfReferentialRoot.model_fields["root"].annotation = _SelfReferentialRoot


def _discriminators(annotation: object) -> list[object]:
    assert get_origin(annotation) is Annotated
    return [
        m.discriminator for m in get_args(annotation)[1:] if isinstance(m, FieldInfo)
    ]


def test_non_rootmodel_is_returned_unchanged() -> None:
    assert denoted_type(_ArmA) is _ArmA
    assert denoted_type(_Arms) is _Arms


def test_rootmodel_denotes_its_root_with_the_root_field_info() -> None:
    """Pydantic lifts the root's `Field(discriminator=...)` onto the root
    `FieldInfo`; the denoted type has it again, as the alias does."""
    denoted = denoted_type(_NamedArms)

    assert get_args(denoted)[0] == (_ArmA | _ArmB)
    assert "type" in _discriminators(denoted)


def test_nested_rootmodels_peel_to_the_innermost_root() -> None:
    denoted = denoted_type(_RenamedArms)

    assert get_args(denoted)[0] == (_ArmA | _ArmB)
    assert "type" in _discriminators(denoted)


def test_model_root_denotes_the_model() -> None:
    class Wrapped(RootModel[_ArmA]):
        pass

    assert get_args(denoted_type(Wrapped))[0] is _ArmA


def test_self_referential_root_raises() -> None:
    with pytest.raises(TypeError, match="Self-referential RootModel"):
        denoted_type(_SelfReferentialRoot)


class _UnannotatedRoot(RootModel[int]):
    """A RootModel whose root `FieldInfo` has lost its annotation."""


_UnannotatedRoot.model_fields["root"].annotation = None


def test_unannotated_root_raises() -> None:
    with pytest.raises(TypeError, match="has no root annotation"):
        denoted_type(_UnannotatedRoot)
