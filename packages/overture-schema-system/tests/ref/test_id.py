from overture.schema.system.feature import Feature
from overture.schema.system.ref.id import Identified


class TestIdentifiedFeature:
    """
    Tests to validate that the `Identified` model plays nicely with the `Feature` model.
    """

    class IdentifiedFeature(Identified, Feature):
        pass

    def test_id_required_in_model_fields(self):
        id_field = TestIdentifiedFeature.IdentifiedFeature.model_fields["id"]

        assert id_field.is_required()

    def test_description_same_in_model_fields(self):
        base_id_field = Identified.model_fields["id"]
        derived_id_field = TestIdentifiedFeature.IdentifiedFeature.model_fields["id"]

        assert base_id_field.description == derived_id_field.description
