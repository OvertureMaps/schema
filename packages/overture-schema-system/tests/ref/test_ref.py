import pytest

from overture.schema.system.ref.id import Identified
from overture.schema.system.ref.ref import Reference, Relationship


def test_reference_err_not_a_relationship() -> None:
    with pytest.raises(TypeError):
        Reference("foo", Identified)  # type: ignore[arg-type]


def test_reference_err_relatee_not_a_feature_type() -> None:
    with pytest.raises(TypeError):
        Reference(Relationship.COMPOSITION, str)  # type: ignore[arg-type]


def test_reference_err_relatee_not_a_type() -> None:
    with pytest.raises(TypeError):
        Reference(Relationship.COMPOSITION, "foo")  # type: ignore[arg-type]


def test_reference_err_role_not_snake_case() -> None:
    with pytest.raises(ValueError):
        Reference(Relationship.COMPOSITION, Identified, role="NotSnakeCase")


def test_reference_err_role_empty() -> None:
    with pytest.raises(ValueError):
        Reference(Relationship.COMPOSITION, Identified, role="")


def test_reference_err_role_has_spaces() -> None:
    with pytest.raises(ValueError):
        Reference(Relationship.COMPOSITION, Identified, role="has spaces")


@pytest.mark.parametrize("relationship", tuple(Relationship))
def test_reference_ok_without_role(relationship: Relationship) -> None:
    ref = Reference(relationship, Identified)

    assert ref.relationship is relationship
    assert ref.relatee is Identified
    assert ref.role is None


@pytest.mark.parametrize("relationship", tuple(Relationship))
def test_reference_ok_with_role(relationship: Relationship) -> None:
    ref = Reference(relationship, Identified, role="belongs_to")

    assert ref.relationship is relationship
    assert ref.relatee is Identified
    assert ref.role == "belongs_to"


@pytest.mark.parametrize(
    "role",
    ["part_of", "child_of", "connects_to", "boundary_of", "has_as_capital"],
)
def test_reference_valid_roles(role: str) -> None:
    ref = Reference(Relationship.COMPOSITION, Identified, role=role)
    assert ref.role == role
