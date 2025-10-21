import itertools
import re
from typing import Annotated, cast, get_args, get_origin

import pytest
from overture.schema.core.scoping import (
    Heading,
    LinearlyReferencedPosition,
    Scope,
    Side,
    TravelMode,
    VehicleSelector,
    scoped,
)
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import (
    ModelConstraint,
    RequireAnyOfConstraint,
)
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


class TestScope:
    @pytest.mark.parametrize("scope", list(Scope))
    def test__field_optional(self, scope: Scope) -> None:
        field = scope._field("foo", False)
        origin = get_origin(field)
        args = get_args(field)

        assert origin is Annotated
        assert isinstance(args[1], FieldInfo)
        assert args[1].default is None

    @pytest.mark.parametrize("scope", list(Scope))
    def test__field_required(self, scope: Scope) -> None:
        field = scope._field("bar", True)
        origin = get_origin(field)
        args = get_args(field)

        assert origin is Annotated
        assert isinstance(args[1], FieldInfo)
        assert args[1].default is PydanticUndefined


class TestScoped:
    def test_error_applied_to_non_class(self) -> None:
        with pytest.raises(TypeError, match="`@scoped` can only be applied to classes"):

            class Foo:
                @scoped(Scope.GEOMETRIC_POSITION)
                def bar(self) -> int:
                    return 123

    def test_error_applied_to_non_base_model(self) -> None:
        with pytest.raises(
            TypeError,
            match="`@scoped` target class must inherit from `pydantic.main.BaseModel`",
        ):

            @scoped(Scope.HEADING)
            class Baz:
                pass

    @pytest.mark.parametrize("scope", Scope._top_level_scopes())
    def test_error_conflicting_model_field_top_level(self, scope: Scope) -> None:
        with pytest.raises(
            TypeError,
            match=f"can't apply `@scoped` to model `Qux`: the following model fields conflict with fields `@scoped` needs to create: {scope._field_name}",
        ):

            @scoped(scope)
            class Qux(BaseModel):
                exec(f"{scope._field_name}: int = 42")

    @pytest.mark.parametrize("scope", Scope._when_scopes())
    def test_error_conflicting_model_field_when(self, scope: Scope) -> None:
        with pytest.raises(
            TypeError,
            match="can't apply `@scoped` to model `Corge`: the following model fields conflict with fields `@scoped` needs to create: when",
        ):

            @scoped(scope)
            class Corge(BaseModel):
                when: int = 42

    @pytest.mark.parametrize("scope", Scope._when_scopes())
    def test_error_model_already_has_When_attribute(self, scope: Scope) -> None:
        with pytest.raises(
            TypeError,
            match="can't apply `@scoped` to model class `Garply`: there is already a class attribute `When`",
        ):

            @scoped(scope)
            class Garply(BaseModel):
                class When:
                    pass

    def test_error_no_scopes(self) -> None:
        with pytest.raises(
            ValueError,
            match="for `@scoped`, at least one scope must be specified, but both `optional` and `required` are empty",
        ):

            @scoped()
            class Foo(BaseModel):
                pass

    def test_error_repeated_scopes(self) -> None:
        with pytest.raises(
            ValueError,
            match="for `@scoped`, `required` must not repeat any values from `optional`, but it has the following repeat values: temporal",
        ):

            @scoped(Scope.TEMPORAL, required=Scope.TEMPORAL)
            class Bar(BaseModel):
                pass

    def test_error_required_not_scope_or_iterable(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape(
                "for `@scoped`, required must be a `Scope`, or an `Iterable[Scope]` (such as a `list` or `tuple`), but the given value of type int is none of these"
            ),
        ):

            @scoped(required=cast(Scope, 42))
            class Baz(BaseModel):
                pass

    def test_error_required_iterable_non_scope(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape(
                "for `@scoped`, all elements of `required` must be a `Scope`, but at least one value in (<Scope.SIDE: 'side'>, 42) is not"
            ),
        ):

            @scoped(required=(Scope.SIDE, cast(Scope, 42)))
            class Qux(BaseModel):
                pass

    @pytest.mark.parametrize(
        "scope,required", itertools.product(Scope._top_level_scopes(), (False, True))
    )
    def test_single_scope_top_level(self, scope: Scope, required: bool) -> None:
        if required:
            o = []
            r = [scope]
        else:
            o = [scope]
            r = []

        @scoped(*o, required=r)
        class SingleScoped(BaseModel):
            pass

        assert len(SingleScoped.model_fields) == 1

        field_info = SingleScoped.model_fields[scope._field_name]
        assert field_info.is_required() == required

    @pytest.mark.parametrize(
        "scope,required", itertools.product(Scope._when_scopes(), (False, True))
    )
    def test_single_scope_when(self, scope: Scope, required: bool) -> None:
        if required:
            o = []
            r = [scope]
        else:
            o = [scope]
            r = []

        @scoped(*o, required=r)
        class SingleScoped(BaseModel):
            pass

        assert len(SingleScoped.model_fields) == 1

        when_field_info = SingleScoped.model_fields["when"]
        assert when_field_info.is_required() == required

        when_class = SingleScoped.When
        assert issubclass(when_class, BaseModel)
        assert len(when_class.model_fields) == 1

        scoped_field_info = when_class.model_fields[scope._field_name]
        assert (
            scoped_field_info.is_required()
        )  # If a single `when` field is optional, the `when` is optional.

    def test_multi_scope_when_all_optional(self) -> None:
        @scoped(Scope.TRAVEL_MODE, Scope.VEHICLE)
        class MultiScopedWhenAllFieldsOptional(BaseModel):
            pass

        assert len(MultiScopedWhenAllFieldsOptional.model_fields) == 1

        when_field_info = MultiScopedWhenAllFieldsOptional.model_fields["when"]
        assert not when_field_info.is_required()

        when_class = MultiScopedWhenAllFieldsOptional.When
        assert issubclass(when_class, BaseModel)
        assert len(when_class.model_fields) == 2

        travel_mode_field_info = when_class.model_fields[Scope.TRAVEL_MODE._field_name]
        assert not travel_mode_field_info.is_required()

        vehicle_field_info = when_class.model_fields[Scope.VEHICLE._field_name]
        assert not vehicle_field_info.is_required()

        model_constraints = ModelConstraint.get_model_constraints(when_class)
        require_any_of = next(
            c for c in model_constraints if isinstance(c, RequireAnyOfConstraint)
        )
        assert sorted(require_any_of.field_names) == [
            Scope.TRAVEL_MODE._field_name,
            Scope.VEHICLE._field_name,
        ]

    def test_multi_scope_when_some_required(self) -> None:
        @scoped(Scope.RECOGNIZED_STATUS, required=(Scope.PURPOSE_OF_USE, Scope.VEHICLE))
        class MultiScopedWhenSomeFieldsRequired(BaseModel):
            pass

        assert len(MultiScopedWhenSomeFieldsRequired.model_fields) == 1

        when_field_info = MultiScopedWhenSomeFieldsRequired.model_fields["when"]
        assert when_field_info.is_required()

        when_class = MultiScopedWhenSomeFieldsRequired.When
        assert issubclass(when_class, BaseModel)
        assert len(when_class.model_fields) == 3

        recognized_status_field_info = when_class.model_fields[
            Scope.RECOGNIZED_STATUS._field_name
        ]
        assert not recognized_status_field_info.is_required()

        purpose_of_use_field_info = when_class.model_fields[
            Scope.PURPOSE_OF_USE._field_name
        ]
        assert purpose_of_use_field_info.is_required()

        vehicle_field_info = when_class.model_fields[Scope.VEHICLE._field_name]
        assert vehicle_field_info.is_required()

    def test_complex_scope(self) -> None:
        @scoped(
            Scope.GEOMETRIC_POSITION,
            Scope.HEADING,
            Scope.VEHICLE,
            required=[Scope.TRAVEL_MODE, Scope.SIDE],
        )
        class Complex(BaseModel):
            pass

        assert len(Complex.model_fields) == 3

        geometric_position_field_info = Complex.model_fields[
            Scope.GEOMETRIC_POSITION._field_name
        ]
        assert not geometric_position_field_info.is_required()
        assert (
            get_args(geometric_position_field_info.annotation)[0]
            is LinearlyReferencedPosition
        )

        when_field_info = Complex.model_fields["when"]
        assert when_field_info.is_required()

        when_class = Complex.When
        assert issubclass(when_class, BaseModel)
        assert len(when_class.model_fields) == 3

        heading_field_info = when_class.model_fields[Scope.HEADING._field_name]
        assert not heading_field_info.is_required()
        assert get_args(heading_field_info.annotation)[0] is Heading

        vehicle_field_info = when_class.model_fields[Scope.VEHICLE._field_name]
        assert not vehicle_field_info.is_required()
        vehicle_field_type = get_args(vehicle_field_info.annotation)[0]
        assert get_origin(vehicle_field_type) is list
        assert get_args(vehicle_field_type)[0] is VehicleSelector
        assert any(
            x
            for x in vehicle_field_info.metadata
            if isinstance(x, UniqueItemsConstraint)
        )

        travel_mode_field_info = when_class.model_fields[Scope.TRAVEL_MODE._field_name]
        assert travel_mode_field_info.is_required()
        travel_mode_field_type = travel_mode_field_info.annotation
        assert get_origin(travel_mode_field_type) is list
        assert get_args(travel_mode_field_type)[0] is TravelMode
        assert any(
            x
            for x in travel_mode_field_info.metadata
            if isinstance(x, UniqueItemsConstraint)
        )

        side_field_info = Complex.model_fields[Scope.SIDE._field_name]
        assert side_field_info.is_required()
        assert side_field_info.annotation is Side
