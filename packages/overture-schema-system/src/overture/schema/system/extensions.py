from collections.abc import Callable
from typing import Annotated, Any, NewType, Union, get_args, get_origin

from pydantic import BaseModel

from overture.schema.system import create_model
from overture.schema.system.feature import Feature
from overture.schema.system.model_constraint import ModelConstraint


class Extends:
    """
    Metadata class for specifying which OvertureFeature classes an extension model is allowed to
    extend.
    """

    def __is_overture_feature(self, feature: Any) -> bool:
        origin = get_origin(feature)

        if origin is Annotated:
            return self.__is_overture_feature(get_args(feature)[0])

        if origin is Union:
            for arg in get_args(feature):
                if not self.__is_overture_feature(arg):
                    return False
            return True

        if hasattr(feature, "__supertype__"):
            return self.__is_overture_feature(feature.__supertype__)

        return isinstance(feature, type) and issubclass(feature, Feature)

    def __set_extended_features(self, features: tuple[type[Feature], ...]) -> None:
        for feature in features:
            if not self.__is_overture_feature(feature):
                raise TypeError(
                    f"All arguments must be subclasses of `Feature`, but {repr(feature)} is of type `{type(feature).__name__}`"
                )
        self.__extended_features: tuple[type[Feature], ...] = features

    def __init__(self, *features: type[Feature]):
        self.__set_extended_features(features)

    @property
    def extends(self) -> tuple[type[Feature], ...]:
        return self.__extended_features


class ExtendsConstraint(ModelConstraint):
    def __is_feature(self, feature: Any) -> bool:
        origin = get_origin(feature)

        if origin is Annotated:
            return self.__is_feature(get_args(feature)[0])

        if origin is Union:
            for arg in get_args(feature):
                if not self.__is_feature(arg):
                    return False
            return True

        if hasattr(feature, "__supertype__"):
            return self.__is_feature(feature.__supertype__)

        return isinstance(feature, type) and issubclass(feature, Feature)

    def __set_extended_features(self, *features: type[Feature]) -> None:
        for feature in features:
            if not self.__is_feature(feature):
                raise TypeError(
                    f"All arguments must be subclasses of `Feature`, but {repr(feature)} is of type `{type(feature).__name__}`"
                )
        self.__extended_features: tuple[type[Feature], ...] = features

    def __init__(self, *features: type[Feature]) -> None:
        super().__init__()
        self.__set_extended_features(*features)

    @classmethod
    def _create_internal(
        cls, name: str, *features: type[Feature]
    ) -> "ExtendsConstraint":
        instance = cls.__new__(cls)
        super(ExtendsConstraint, instance).__init__(name)
        instance.__set_extended_features(*features)
        return instance

    @property
    def extends(self) -> tuple[type[Feature], ...]:
        return self.__extended_features


def extends(
    *features: type[Feature] | Any,
) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    A decorator that applies the ExtendsConstraint to a model.

    Args:
        features: One or more OvertureFeature subclasses.

    Returns:
        Callable: A decorator function for the model.
    """

    model_constraint: ExtendsConstraint = ExtendsConstraint._create_internal(
        f"@{extends.__name__}",
        *features,
    )
    return model_constraint.decorate


def extends_classes(feature: type[BaseModel]) -> tuple[type[Feature], ...]:
    """
    Retrieves the OvertureFeature classes that the given extension model is allowed to extend.

    This function inspects the provided extension model and determines which OvertureFeature
    classes it is associated with via the @extends decorator or Extends metadata. This is used
    to identify which Overture features the extension model can be applied to as extension fields.

    Args:
        feature: The extension model to inspect.

    Returns:
        A tuple of OvertureFeature classes that the extension model is allowed to extend.
        Returns an empty tuple if the model doesn't extend any OvertureFeature classes.
    """
    match = next(
        (
            c
            for c in ModelConstraint.get_model_constraints(feature)
            if isinstance(c, ExtendsConstraint)
        ),
        (),
    )
    if match:
        return match.extends

    if hasattr(feature, "__supertype__"):
        tp = feature.__supertype__
        _, *metadata = get_args(tp)
        for meta in metadata:
            if isinstance(meta, Extends):
                return meta.extends

    return ()


def _unwrap_types(tp: Any) -> tuple[type[Feature], ...]:
    origin = get_origin(tp)

    if origin is Annotated:
        return _unwrap_types(get_args(tp)[0])

    if origin is Union:
        classes: list[type[Feature]] = []
        for arg in get_args(tp):
            classes.extend(_unwrap_types(arg))
        return tuple(classes)

    if hasattr(tp, "__supertype__"):
        return _unwrap_types(tp.__supertype__)

    if issubclass(tp, Feature):
        return (tp,)

    return ()


def create_extended_model(model: Any, extensions: dict[Any, type[BaseModel]]) -> Any:
    """
    Creates an extended model by applying the given extensions.

    Args:
        model: The base model to extend.
        extensions: A dictionary mapping types to their extensions.

    Returns:
        The extended model, or the original model if no extensions apply.
    """

    origin = get_origin(model)

    if origin is Annotated:
        tp, *metadata = get_args(model)
        return Annotated.__class_getitem__(  # type: ignore[attr-defined]
            (create_extended_model(tp, extensions), *metadata)
        )

    if origin is Union:
        return Union[  # noqa: UP007
            tuple(create_extended_model(tp, extensions) for tp in get_args(model))
        ]

    if hasattr(model, "__supertype__"):
        return NewType(
            model.__name__, create_extended_model(model.__supertype__, extensions)
        )

    ext: dict[str, tuple[Any, None]] = {
        type.name: (cls | None, None)
        for type, cls in extensions.items()
        if any(issubclass(model, _unwrap_types(base)) for base in extends_classes(cls))
    }

    if ext:
        return create_model(
            model.__name__,
            __base__=model,
            __doc__=model.__doc__,
            __module__=model.__module__,
            **ext,  # type: ignore[arg-type]
        )

    return model
