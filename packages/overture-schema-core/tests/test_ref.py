import pytest
from overture.schema.core.models import Feature
from overture.schema.core.ref import Reference, Relationship


def test_reference_err_not_a_relationship() -> None:
    with pytest.raises(TypeError):
        Reference("foo", Feature)  # type: ignore[arg-type]


def test_reference_err_referee_not_a_feature_type() -> None:
    with pytest.raises(TypeError):
        Reference(Relationship.BELONGS_TO, str)  # type: ignore[arg-type]


def test_reference_err_referee_not_a_type() -> None:
    with pytest.raises(TypeError):
        Reference(Relationship.BELONGS_TO, "foo")  # type: ignore[arg-type]


@pytest.mark.parametrize("relationship", tuple(Relationship))
def test_reference_ok(relationship: Relationship) -> None:
    ref = Reference(relationship, Feature)

    assert ref.relationship is relationship
    assert ref.relatee is Feature
