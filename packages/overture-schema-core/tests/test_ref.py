import pytest
from overture.schema.core.models import Feature
from overture.schema.core.ref import RefersTo, Relationship


def test_refers_to_err_referee_not_a_type() -> None:
    with pytest.raises(TypeError):
        RefersTo("foo", Relationship.BELONGS_TO) # type: ignore[arg-type]


def test_refers_to_err_referee_not_a_feature_type() -> None:
    with pytest.raises(TypeError):
        RefersTo(str, Relationship.BELONGS_TO) # type: ignore[arg-type]


def test_refers_to_err_not_a_relationship() -> None:
    with pytest.raises(TypeError):
        RefersTo(Feature, "foo") # type: ignore[arg-type]


@pytest.mark.parametrize("relationship", Relationship)
def test_refers_to_ok(relationship: Relationship) -> None:
    refers_to = RefersTo(Feature, relationship)

    assert refers_to.referee is Feature
    assert refers_to.relationship is relationship
