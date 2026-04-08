from overture.schema.system.discovery import discover_models


def test_overture_feature_models_are_official() -> None:
    models = discover_models()
    for key in models:
        if "feature" in key.tags:
            assert "overture" in key.tags, (
                f"Model {key.name} is missing 'overture:official' tag."
            )
