import inspect

import pydantic
from pydantic import BaseModel, computed_field

from overture.schema.system import create_model
from overture.schema.system.metadata import Key, Metadata


def _keyword_parameters(f: object) -> set[str]:
    return {
        p.name
        for p in inspect.signature(f).parameters.values()  # type: ignore[arg-type]
        if p.kind is inspect.Parameter.KEYWORD_ONLY
    }


class TestCreateModel:
    def test_parameters_mirror_pydantic(self) -> None:
        # `__validators__` is left out: pydantic 2.14 replaces it with `__namespace__` and
        # deprecates it in V3.
        assert _keyword_parameters(create_model) == (
            _keyword_parameters(pydantic.create_model) - {"__validators__"}
        ) | {"__metadata__"}

    def test_namespace_adds_attributes_and_keeps_base_metadata(self) -> None:
        class Base(BaseModel):
            foo: int

        metadata = Metadata()
        metadata[Key("test")] = "value"
        metadata.attach_to(Base)

        def doubled(self: Base) -> int:
            return 2 * self.foo

        Model = create_model(
            "Model",
            __base__=Base,
            __namespace__={"doubled": computed_field(property(doubled))},  # type: ignore[prop-decorator]
        )

        assert Model(foo=21).model_dump() == {"foo": 21, "doubled": 42}
        assert Metadata.retrieve_from(Model) == metadata
