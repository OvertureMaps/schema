"""Tests for hashability of all scope and related classes."""

from overture.schema.core.models import GeometricRangeScope
from overture.schema.foundation.primitive.geometry import Geometry
from overture.schema.transportation.enums import (
    AccessType,
    DestinationLabelType,
    Heading,
    PurposeOfUse,
    RecognizedStatus,
    TravelMode,
    VehicleComparison,
    VehicleDimension,
)
from overture.schema.transportation.models import (
    AccessRestrictionRule,
    AccessRestrictionWhenClause,
    ConnectorReference,
    DestinationLabels,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    SequenceEntry,
    Speed,
    TemporalScope,
    TravelModeScope,
    VehicleScope,
    VehicleScopeRule,
)
from shapely.geometry import Point


class TestGeometricRangeScopeHashability:
    """Test hashability of GeometricRangeScope."""

    def test_geometric_range_scope_with_none_between(self) -> None:
        """Test GeometricRangeScope with None between field."""
        scope1 = GeometricRangeScope()
        scope2 = GeometricRangeScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_geometric_range_scope_with_between_values(self) -> None:
        """Test GeometricRangeScope with between field values."""
        scope1 = GeometricRangeScope(between=[0.0, 0.5])
        scope2 = GeometricRangeScope(between=[0.0, 0.5])
        scope3 = GeometricRangeScope(between=[0.5, 1.0])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_geometric_range_scope_in_set(self) -> None:
        """Test that GeometricRangeScope can be used in sets."""
        scope1 = GeometricRangeScope(between=[0.0, 0.5])
        scope2 = GeometricRangeScope(between=[0.0, 0.5])
        scope3 = GeometricRangeScope(between=[0.5, 1.0])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2  # scope1 and scope2 are equal


class TestTemporalScopeHashability:
    """Test hashability of TemporalScope."""

    def test_temporal_scope_with_none_during(self) -> None:
        """Test TemporalScope with None during field."""
        scope1 = TemporalScope()
        scope2 = TemporalScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_temporal_scope_with_during_values(self) -> None:
        """Test TemporalScope with during field values."""
        scope1 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope2 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope3 = TemporalScope(during="Sa-Su")

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_temporal_scope_in_set(self) -> None:
        """Test that TemporalScope can be used in sets."""
        scope1 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope2 = TemporalScope(during="Mo-Fr 08:00-17:00")
        scope3 = TemporalScope(during="Sa-Su")

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestHeadingScopeHashability:
    """Test hashability of HeadingScope."""

    def test_heading_scope_with_none_heading(self) -> None:
        """Test HeadingScope with None heading field."""
        scope1 = HeadingScope()
        scope2 = HeadingScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_heading_scope_with_heading_values(self) -> None:
        """Test HeadingScope with heading field values."""
        scope1 = HeadingScope(heading="forward")
        scope2 = HeadingScope(heading="forward")
        scope3 = HeadingScope(heading="backward")

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_heading_scope_in_set(self) -> None:
        """Test that HeadingScope can be used in sets."""
        scope1 = HeadingScope(heading="forward")
        scope2 = HeadingScope(heading="forward")
        scope3 = HeadingScope(heading="backward")

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestTravelModeScopeHashability:
    """Test hashability of TravelModeScope."""

    def test_travel_mode_scope_with_none_mode(self) -> None:
        """Test TravelModeScope with None mode field."""
        scope1 = TravelModeScope()
        scope2 = TravelModeScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_travel_mode_scope_with_mode_values(self) -> None:
        """Test TravelModeScope with mode field values."""
        scope1 = TravelModeScope(mode=[TravelMode.CAR])
        scope2 = TravelModeScope(mode=[TravelMode.CAR])
        scope3 = TravelModeScope(mode=[TravelMode.FOOT, TravelMode.BICYCLE])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_travel_mode_scope_in_set(self) -> None:
        """Test that TravelModeScope can be used in sets."""
        scope1 = TravelModeScope(mode=[TravelMode.CAR])
        scope2 = TravelModeScope(mode=[TravelMode.CAR])
        scope3 = TravelModeScope(mode=[TravelMode.FOOT])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestPurposeOfUseScopeHashability:
    """Test hashability of PurposeOfUseScope."""

    def test_purpose_of_use_scope_with_none_using(self) -> None:
        """Test PurposeOfUseScope with None using field."""
        scope1 = PurposeOfUseScope()
        scope2 = PurposeOfUseScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_purpose_of_use_scope_with_using_values(self) -> None:
        """Test PurposeOfUseScope with using field values."""
        scope1 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope2 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope3 = PurposeOfUseScope(using=[PurposeOfUse.AT_DESTINATION])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_purpose_of_use_scope_in_set(self) -> None:
        """Test that PurposeOfUseScope can be used in sets."""
        scope1 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope2 = PurposeOfUseScope(using=[PurposeOfUse.TO_DELIVER])
        scope3 = PurposeOfUseScope(using=[PurposeOfUse.AT_DESTINATION])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestRecognizedStatusScopeHashability:
    """Test hashability of RecognizedStatusScope."""

    def test_recognized_status_scope_with_none_recognized(self) -> None:
        """Test RecognizedStatusScope with None recognized field."""
        scope1 = RecognizedStatusScope()
        scope2 = RecognizedStatusScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_recognized_status_scope_with_recognized_values(self) -> None:
        """Test RecognizedStatusScope with recognized field values."""
        scope1 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope2 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope3 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_PRIVATE])

        assert hash(scope1) == hash(scope2)
        assert hash(scope1) != hash(scope3)
        assert scope1 == scope2
        assert scope1 != scope3

    def test_recognized_status_scope_in_set(self) -> None:
        """Test that RecognizedStatusScope can be used in sets."""
        scope1 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope2 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_EMPLOYEE])
        scope3 = RecognizedStatusScope(recognized=[RecognizedStatus.AS_PRIVATE])

        scope_set = {scope1, scope2, scope3}
        assert len(scope_set) == 2


class TestSpeedHashability:
    """Test hashability of Speed."""

    def test_speed_hashability(self) -> None:
        """Test Speed hashability."""
        speed1 = Speed(value=50.0, unit="km/h")
        speed2 = Speed(value=50.0, unit="km/h")
        speed3 = Speed(value=30.0, unit="mph")

        assert hash(speed1) == hash(speed2)
        assert hash(speed1) != hash(speed3)
        assert speed1 == speed2
        assert speed1 != speed3

    def test_speed_in_set(self) -> None:
        """Test that Speed can be used in sets."""
        speed1 = Speed(value=50.0, unit="km/h")
        speed2 = Speed(value=50.0, unit="km/h")
        speed3 = Speed(value=30.0, unit="mph")

        speed_set = {speed1, speed2, speed3}
        assert len(speed_set) == 2


class TestVehicleConstraintHashability:
    """Test hashability of VehicleConstraint."""

    def test_vehicle_constraint_hashability(self) -> None:
        """Test VehicleConstraint hashability."""
        constraint1 = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint3 = VehicleScopeRule(
            dimension=VehicleDimension.HEIGHT,
            comparison=VehicleComparison.LESS_THAN,
            value=3.8,
        )

        assert hash(constraint1) == hash(constraint2)
        assert hash(constraint1) != hash(constraint3)
        assert constraint1 == constraint2
        assert constraint1 != constraint3

    def test_vehicle_constraint_in_set(self) -> None:
        """Test that VehicleConstraint can be used in sets."""
        constraint1 = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint3 = VehicleScopeRule(
            dimension=VehicleDimension.HEIGHT,
            comparison=VehicleComparison.LESS_THAN,
            value=3.8,
        )

        constraint_set = {constraint1, constraint2, constraint3}
        assert len(constraint_set) == 2


class TestVehicleScopeHashability:
    """Test hashability of VehicleScope."""

    def test_vehicle_scope_with_none_vehicle(self) -> None:
        """Test VehicleScope with None vehicle field."""
        scope1 = VehicleScope()
        scope2 = VehicleScope()

        assert hash(scope1) == hash(scope2)
        assert scope1 == scope2

    def test_vehicle_scope_with_vehicle_values(self) -> None:
        """Test VehicleScope with vehicle field values."""
        constraint = VehicleScopeRule(
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

    def test_vehicle_scope_in_set(self) -> None:
        """Test that VehicleScope can be used in sets."""
        constraint1 = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )
        constraint2 = VehicleScopeRule(
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

    def test_access_restriction_when_clause_empty(self) -> None:
        """Test AccessRestrictionWhenClause with minimal fields set."""
        # At least one property must be set due to @min_properties(1)
        clause1 = AccessRestrictionWhenClause(heading=Heading.FORWARD)
        clause2 = AccessRestrictionWhenClause(heading=Heading.FORWARD)

        assert hash(clause1) == hash(clause2)
        assert clause1 == clause2

    def test_access_restriction_when_clause_with_values(self) -> None:
        """Test AccessRestrictionWhenClause with various field values."""

        clause1 = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading=Heading.FORWARD,
            mode=[TravelMode.CAR],
            using=[PurposeOfUse.TO_DELIVER],
        )
        clause2 = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading=Heading.FORWARD,
            mode=[TravelMode.CAR],
            using=[PurposeOfUse.TO_DELIVER],
        )
        clause3 = AccessRestrictionWhenClause(during="Sa-Su", heading=Heading.BACKWARD)

        assert hash(clause1) == hash(clause2)
        assert hash(clause1) != hash(clause3)
        assert clause1 == clause2
        assert clause1 != clause3

    def test_access_restriction_when_clause_in_set(self) -> None:
        """Test that AccessRestrictionWhenClause can be used in sets."""
        clause1 = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")
        clause2 = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")
        clause3 = AccessRestrictionWhenClause(during="Sa-Su")

        clause_set = {clause1, clause2, clause3}
        assert len(clause_set) == 2


class TestAccessRestrictionRuleHashability:
    """Test hashability of AccessRestrictionRule."""

    def test_access_restriction_rule_basic(self) -> None:
        """Test AccessRestrictionRule basic hashability."""
        rule1 = AccessRestrictionRule(access_type=AccessType.DENIED)
        rule2 = AccessRestrictionRule(access_type=AccessType.DENIED)
        rule3 = AccessRestrictionRule(access_type=AccessType.ALLOWED)

        assert hash(rule1) == hash(rule2)
        assert hash(rule1) != hash(rule3)
        assert rule1 == rule2
        assert rule1 != rule3

    def test_access_restriction_rule_with_when_clause(self) -> None:
        """Test AccessRestrictionRule with when clause."""
        when_clause = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00", heading=Heading.FORWARD
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

    def test_access_restriction_rule_in_set(self) -> None:
        """Test that AccessRestrictionRule can be used in sets."""
        when_clause = AccessRestrictionWhenClause(during="Mo-Fr 08:00-17:00")

        rule1 = AccessRestrictionRule(access_type=AccessType.DENIED, when=when_clause)
        rule2 = AccessRestrictionRule(access_type=AccessType.DENIED, when=when_clause)
        rule3 = AccessRestrictionRule(access_type=AccessType.ALLOWED)

        rule_set = {rule1, rule2, rule3}
        assert len(rule_set) == 2

    def test_complex_access_restriction_rule_hashability(self) -> None:
        """Test complex AccessRestrictionRule with all fields."""
        constraint = VehicleScopeRule(
            dimension=VehicleDimension.WEIGHT,
            comparison=VehicleComparison.GREATER_THAN,
            value=7.5,
            unit="t",
        )

        when_clause = AccessRestrictionWhenClause(
            during="Mo-Fr 08:00-17:00",
            heading=Heading.FORWARD,
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


class TestGeometryHashability:
    """Test hashability of Geometry."""

    def test_geometry_hashability(self) -> None:
        """Test Geometry hashability."""
        # Note: Using Point geometry for testing
        geom1 = Geometry(Point(1.0, 2.0))
        geom2 = Geometry(Point(1.0, 2.0))
        geom3 = Geometry(Point(3.0, 4.0))

        assert hash(geom1) == hash(geom2)
        assert hash(geom1) != hash(geom3)
        assert geom1 == geom2
        assert geom1 != geom3

    def test_geometry_in_set(self) -> None:
        """Test that Geometry can be used in sets."""

        geom1 = Geometry(Point(1.0, 2.0))
        geom2 = Geometry(Point(1.0, 2.0))
        geom3 = Geometry(Point(3.0, 4.0))

        geom_set = {geom1, geom2, geom3}
        assert len(geom_set) == 2


class TestConnectorReferenceHashability:
    """Test hashability of ConnectorReference."""

    def test_connector_reference_hashability(self) -> None:
        """Test ConnectorReference hashability."""
        ref1 = ConnectorReference(connector_id="conn_01", at=0.5)
        ref2 = ConnectorReference(connector_id="conn_01", at=0.5)
        ref3 = ConnectorReference(connector_id="conn_02", at=0.3)

        assert hash(ref1) == hash(ref2)
        assert hash(ref1) != hash(ref3)
        assert ref1 == ref2
        assert ref1 != ref3

    def test_connector_reference_in_set(self) -> None:
        """Test that ConnectorReference can be used in sets."""
        ref1 = ConnectorReference(connector_id="conn_01", at=0.5)
        ref2 = ConnectorReference(connector_id="conn_01", at=0.5)
        ref3 = ConnectorReference(connector_id="conn_02", at=0.3)

        ref_set = {ref1, ref2, ref3}
        assert len(ref_set) == 2


class TestDestinationLabelsHashability:
    """Test hashability of DestinationLabels."""

    def test_destination_labels_hashability(self) -> None:
        """Test DestinationLabels hashability."""
        label1 = DestinationLabels(
            value="Main Street", type=DestinationLabelType.STREET
        )
        label2 = DestinationLabels(
            value="Main Street", type=DestinationLabelType.STREET
        )
        label3 = DestinationLabels(
            value="Highway 101", type=DestinationLabelType.ROUTE_REF
        )

        assert hash(label1) == hash(label2)
        assert hash(label1) != hash(label3)
        assert label1 == label2
        assert label1 != label3

    def test_destination_labels_with_different_values(self) -> None:
        """Test DestinationLabels with different values but same type."""
        label1 = DestinationLabels(
            value="Main Street", type=DestinationLabelType.STREET
        )
        label2 = DestinationLabels(value="Oak Avenue", type=DestinationLabelType.STREET)

        assert hash(label1) != hash(label2)
        assert label1 != label2

    def test_destination_labels_with_different_types(self) -> None:
        """Test DestinationLabels with same value but different types."""
        label1 = DestinationLabels(
            value="Route 66", type=DestinationLabelType.ROUTE_REF
        )
        label2 = DestinationLabels(
            value="Route 66", type=DestinationLabelType.TOWARD_ROUTE_REF
        )

        assert hash(label1) != hash(label2)
        assert label1 != label2

    def test_destination_labels_in_set(self) -> None:
        """Test that DestinationLabels can be used in sets."""
        label1 = DestinationLabels(
            value="Main Street", type=DestinationLabelType.STREET
        )
        label2 = DestinationLabels(
            value="Main Street", type=DestinationLabelType.STREET
        )
        label3 = DestinationLabels(
            value="Highway 101", type=DestinationLabelType.ROUTE_REF
        )

        label_set = {label1, label2, label3}
        assert len(label_set) == 2


class TestSequenceEntryHashability:
    """Test hashability of SequenceEntry."""

    def test_sequence_entry_hashability(self) -> None:
        """Test SequenceEntry hashability."""
        entry1 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry2 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry3 = SequenceEntry(connector_id="conn_02", segment_id="seg_02")

        assert hash(entry1) == hash(entry2)
        assert hash(entry1) != hash(entry3)
        assert entry1 == entry2
        assert entry1 != entry3

    def test_sequence_entry_with_different_connector_ids(self) -> None:
        """Test SequenceEntry with different connector IDs."""
        entry1 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry2 = SequenceEntry(connector_id="conn_02", segment_id="seg_01")

        assert hash(entry1) != hash(entry2)
        assert entry1 != entry2

    def test_sequence_entry_with_different_segment_ids(self) -> None:
        """Test SequenceEntry with different segment IDs."""
        entry1 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry2 = SequenceEntry(connector_id="conn_01", segment_id="seg_02")

        assert hash(entry1) != hash(entry2)
        assert entry1 != entry2

    def test_sequence_entry_in_set(self) -> None:
        """Test that SequenceEntry can be used in sets."""
        entry1 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry2 = SequenceEntry(connector_id="conn_01", segment_id="seg_01")
        entry3 = SequenceEntry(connector_id="conn_02", segment_id="seg_02")

        entry_set = {entry1, entry2, entry3}
        assert len(entry_set) == 2
