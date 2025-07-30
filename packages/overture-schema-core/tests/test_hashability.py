"""Tests for hashability of all scope and related classes."""

from overture.schema.core.scoping import (
    GeometricRangeScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TemporalScope,
    TravelModeScope,
    VehicleScope,
)
from overture.schema.core.transportation import (
    PurposeOfUse,
    RecognizedStatus,
    Speed,
    TravelMode,
    VehicleComparison,
    VehicleConstraint,
    VehicleDimension,
)
from overture.schema.transportation.shared import (
    AccessRestrictionRule,
    AccessRestrictionWhenClause,
    AccessType,
)


class TestGeometricRangeScopeHashability:
    """Test hashability of GeometricRangeScope."""

    def test_geometric_range_scope_with_none_between(self):
        """Test GeometricRangeScope with None between field."""
        scope1 = GeometricRangeScope()
        scope2 = GeometricRangeScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_geometric_range_scope_with_between_values(self):
        """Test GeometricRangeScope with between field values."""
        scope1 = GeometricRangeScope(between=[0.0, 0.5])
        scope2 = GeometricRangeScope(between=[0.0, 0.5])
        scope3 = GeometricRangeScope(between=[0.5, 1.0])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_geometric_range_scope_in_set(self):
        """Test that GeometricRangeScope can be used in sets."""
        scope1 = GeometricRangeScope(between=[0.0, 0.5])
        scope2 = GeometricRangeScope(between=[0.0, 0.5])
        scope3 = GeometricRangeScope(between=[0.5, 1.0])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2  # scope1 and scope2 are equal


class TestTemporalScopeHashability:
    """Test hashability of TemporalScope."""

    def test_temporal_scope_with_none_during(self):
        """Test TemporalScope with None during field."""
        scope1 = TemporalScope()
        scope2 = TemporalScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_temporal_scope_with_during_values(self):
        """Test TemporalScope with during field values."""
        scope1 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope2 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope3 = TemporalScope(during="Sa-Su")

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_temporal_scope_in_set(self):
        """Test that TemporalScope can be used in sets."""
        scope1 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope2 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope3 = TemporalScope(during="Sa-Su")

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestHeadingScopeHashability:
    """Test hashability of HeadingScope."""

    def test_heading_scope_with_none_heading(self):
        """Test HeadingScope with None heading field."""
        scope1 = HeadingScope()
        scope2 = HeadingScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_heading_scope_with_heading_values(self):
        """Test HeadingScope with heading field values."""
        scope1 = HeadingScope(heading="forward")
        scope2 = HeadingScope(heading="forward")
        scope3 = HeadingScope(heading="backward")

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_heading_scope_in_set(self):
        """Test that HeadingScope can be used in sets."""
        scope1 = HeadingScope(heading="forward")
        scope2 = HeadingScope(heading="forward")
        scope3 = HeadingScope(heading="backward")

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestTravelModeScopeHashability:
    """Test hashability of TravelModeScope."""

    def test_travel_mode_scope_with_none_mode(self):
        """Test TravelModeScope with None mode field."""
        scope1 = TravelModeScope()
        scope2 = TravelModeScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_travel_mode_scope_with_mode_values(self):
        """Test TravelModeScope with mode field values."""
        scope1 = TravelModeScope(mode=[TravelMode.CAR])
        scope2 = TravelModeScope(mode=[TravelMode.CAR])
        scope3 = TravelModeScope(mode=[TravelMode.FOOT, TravelMode.BIKE])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_travel_mode_scope_in_set(self):
        """Test that TravelModeScope can be used in sets."""
        scope1 = TravelModeScope(mode=[TravelMode.CAR])
        scope2 = TravelModeScope(mode=[TravelMode.CAR])
        scope3 = TravelModeScope(mode=[TravelMode.FOOT])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestPurposeOfUseScopeHashability:
    """Test hashability of PurposeOfUseScope."""

    def test_purpose_of_use_scope_with_none_using(self):
        """Test PurposeOfUseScope with None using field."""
        scope1 = PurposeOfUseScope()
        scope2 = PurposeOfUseScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_purpose_of_use_scope_with_using_values(self):
        """Test PurposeOfUseScope with using field values."""
        scope1 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope2 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope3 = PurposeOfUseScope(using=[PurposeOfUse.AT_DESTINATION])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_purpose_of_use_scope_in_set(self):
        """Test that PurposeOfUseScope can be used in sets."""
        scope1 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope2 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope3 = PurposeOfUseScope(using=[PurposeOfUse.AT_DESTINATION])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestRecognizedStatusScopeHashability:
    """Test hashability of RecognizedStatusScope."""

    def test_recognized_status_scope_with_none_recognized(self):
        """Test RecognizedStatusScope with None recognized field."""
        scope1 = RecognizedStatusScope()
        scope2 = RecognizedStatusScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_recognized_status_scope_with_recognized_values(self):
        """Test RecognizedStatusScope with recognized field values."""
        scope1 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope2 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope3 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_CUSTOMER])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_recognized_status_scope_in_set(self):
        """Test that RecognizedStatusScope can be used in sets."""
        scope1 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope2 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope3 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_CUSTOMER])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestSpeedHashability:
    """Test hashability of Speed."""

    def test_speed_hashability(self):
        """Test Speed hashability."""
        speed1 = Speed(value=50.0, unit="km/h")
        speed2 = Speed(value=50.0, unit="km/h")
        speed3 = Speed(value=30.0, unit="mph")

        assert hash(speed1) == hash(speed2)
        assert hash(speed1) != hash(speed3)
        assert speed1 == speed2
        assert speed1 != speed3

    def test_speed_in_set(self):
        """Test that Speed can be used in sets."""
        speed1 = Speed(value=50.0, unit="km/h")
        speed2 = Speed(value=50.0, unit="km/h")
        speed3 = Speed(value=30.0, unit="mph")

        speed_set = {speed1, speed2, speed3}
        assert len(speed_set) == 2


class TestVehicleConstraintHashability:
    """Test hashability of VehicleConstraint."""

    def test_vehicle_constraint_hashability(self):
        """Test VehicleConstraint hashability."""
        constraint1 = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint3 = VehicleConstraint(
            dimension=VehicleDimension.HEIGHT,
            comparison=VehicleComparison.LESS_THAN,
            value=3.8,
        )

        assert hash(constraint1) == hash(constraint2)
        assert hash(constraint1) != hash(constraint3)
        assert constraint1 == constraint2
        assert constraint1 != constraint3

    def test_vehicle_constraint_in_set(self):
        """Test that VehicleConstraint can be used in sets."""
        constraint1 = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint3 = VehicleConstraint(
            dimension=VehicleDimension.HEIGHT,
            comparison=VehicleComparison.LESS_THAN,
            value=3.8,
        )

        constraint_set = {constraint1, constraint2, constraint3}
        assert len(constraint_set) == 2


class TestVehicleScopeHashability:
    """Test hashability of VehicleScope."""

    def test_vehicle_scope_with_none_vehicle(self):
        """Test VehicleScope with None vehicle field."""
        scope1 = VehicleScope()
        scope2 = VehicleScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_vehicle_scope_with_vehicle_values(self):
        """Test VehicleScope with vehicle field values."""
        constraint = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )

        scope1 = VehicleScope(vehicle=[constraint])
        scope2 = VehicleScope(vehicle=[constraint])
        scope3 = VehicleScope()

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_vehicle_scope_in_set(self):
        """Test that VehicleScope can be used in sets."""
        constraint1 = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleConstraint(
            dimension=VehicleDimension.HEIGHT,
            comparison=VehicleComparison.LESS_THAN,
            value=3.8,
        )

        scope1 = VehicleScope(vehicle=[constraint1])
        scope2 = VehicleScope(vehicle=[constraint1])
        scope3 = VehicleScope(vehicle=[constraint2])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestAccessRestrictionWhenClauseHashability:
    """Test hashability of AccessRestrictionWhenClause."""

    def test_access_restriction_when_clause_empty(self):
        """Test AccessRestrictionWhenClause with no fields set."""
        clause1 = AccessRestrictionWhenClause()
        clause2 = AccessRestrictionWhenClause()

        assert hash(clause1) == hash(clause2)
        assert clause1 == clause2

    def test_access_restriction_when_clause_with_values(self):
        """Test AccessRestrictionWhenClause with various field values."""
        clause1 = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading="forward",
            mode=[TravelMode.CAR],
            using=[PurposeOfUse.TO_DELIVER],
        )
        clause2 = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading="forward",
            mode=[TravelMode.CAR],
            using=[PurposeOfUse.TO_DELIVER],
        )
        clause3 = AccessRestrictionWhenClause(during="Sa-Su", heading="backward")

        assert hash(clause1) == hash(clause2)
        assert hash(clause1) != hash(clause3)
        assert clause1 == clause2
        assert clause1 != clause3

    def test_access_restriction_when_clause_in_set(self):
        """Test that AccessRestrictionWhenClause can be used in sets."""
        clause1 = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")
        clause2 = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")
        clause3 = AccessRestrictionWhenClause(during="Sa-Su")

        clause_set = {clause1, clause2, clause3}
        assert len(clause_set) == 2


class TestAccessRestrictionRuleHashability:
    """Test hashability of AccessRestrictionRule."""

    def test_access_restriction_rule_basic(self):
        """Test AccessRestrictionRule basic hashability."""
        rule1 = AccessRestrictionRule(access_type=AccessType.DENIED)
        rule2 = AccessRestrictionRule(access_type=AccessType.DENIED)
        rule3 = AccessRestrictionRule(access_type=AccessType.ALLOWED)

        assert hash(rule1) == hash(rule2)
        assert hash(rule1) != hash(rule3)
        assert rule1 == rule2
        assert rule1 != rule3

    def test_access_restriction_rule_with_when_clause(self):
        """Test AccessRestrictionRule with when clause."""
        when_clause = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00", heading="forward"
        )

        rule1 = AccessRestrictionRule(
            access_type=AccessType.DENIED, when=when_clause, between=[0.0, 0.5]
        )
        rule2 = AccessRestrictionRule(
            access_type=AccessType.DENIED, when=when_clause, between=[0.0, 0.5]
        )
        rule3 = AccessRestrictionRule(access_type=AccessType.DENIED, between=[0.5, 1.0])

        assert hash(rule1) == hash(rule2)
        assert hash(rule1) != hash(rule3)
        assert rule1 == rule2
        assert rule1 != rule3

    def test_access_restriction_rule_in_set(self):
        """Test that AccessRestrictionRule can be used in sets."""
        when_clause = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")

        rule1 = AccessRestrictionRule(access_type=AccessType.DENIED, when=when_clause)
        rule2 = AccessRestrictionRule(access_type=AccessType.DENIED, when=when_clause)
        rule3 = AccessRestrictionRule(access_type=AccessType.ALLOWED)

        rule_set = {rule1, rule2, rule3}
        assert len(rule_set) == 2

    def test_complex_access_restriction_rule_hashability(self):
        """Test complex AccessRestrictionRule with all fields."""
        constraint = VehicleConstraint(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )

        when_clause = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading="forward",
            mode=[TravelMode.CAR, TravelMode.TRUCK],
            using=[PurposeOfUse.TO_DELIVER],
            recognized=[RecognizedStatus.AS_EMPLOYEE],
            vehicle=[constraint],
        )

        rule1 = AccessRestrictionRule(
            access_type=AccessType.DENIED, when=when_clause, between=[0.0, 0.5]
        )
        rule2 = AccessRestrictionRule(
            access_type=AccessType.DENIED, when=when_clause, between=[0.0, 0.5]
        )

        assert hash(rule1) == hash(rule2)
        assert rule1 == rule2

        # Test in set
        rule_set = {rule1, rule2}
        assert len(rule_set) == 1
