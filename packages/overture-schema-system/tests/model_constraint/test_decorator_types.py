"""
Each model-constraint decorator returns the decorated class typed as that class, not as `BaseModel`.

mypy ignores class-decorator return types, so a check written with `@decorator` syntax passes
even when the decorator erases the class (as pyright and ty then do). Calling each decorator as a
function puts its return type in front of mypy.
"""

from pydantic import BaseModel
from typing_extensions import assert_type

from overture.schema.system.model_constraint import (
    FieldEqCondition,
    NoExtraFieldsConstraint,
    forbid_if,
    min_fields_set,
    no_extra_fields,
    radio_group,
    require_any_of,
    require_any_true,
    require_if,
)


class Model(BaseModel):
    f: int | None = None
    g: int | None = None
    b: bool | None = None
    c: bool | None = None


def test_decorators_preserve_the_decorated_class_type() -> None:
    decorated = [
        assert_type(NoExtraFieldsConstraint().decorate(Model), type[Model]),
        assert_type(no_extra_fields(Model), type[Model]),
        assert_type(require_if(["f"], FieldEqCondition("g", 1))(Model), type[Model]),
        assert_type(forbid_if(["f"], FieldEqCondition("g", 1))(Model), type[Model]),
        assert_type(require_any_of("f", "g")(Model), type[Model]),
        assert_type(require_any_true(FieldEqCondition("b", True))(Model), type[Model]),
        assert_type(radio_group("b", "c")(Model), type[Model]),
        assert_type(min_fields_set(1)(Model), type[Model]),
    ]

    for model_class in decorated:
        assert issubclass(model_class, Model)
