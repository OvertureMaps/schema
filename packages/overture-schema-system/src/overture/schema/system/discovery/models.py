"""Key types identifying registered models and tag providers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelKey:
    """Key identifying a registered model by name, entry point, and tags.

    Attributes
    ----------
    name : str
        Friendly name derived from the entry point key.
    entry_point : str
        Entry point value in `"module:Class"` format.
    tags : frozenset[str]
        Tags associated with the model.
    """

    name: str
    entry_point: str
    tags: frozenset[str]


@dataclass(frozen=True, slots=True)
class TagProviderKey:
    """Key identifying a registered tag provider by name, entry point, and package.

    Attributes
    ----------
    name : str
        Friendly name derived from the entry point key.
    entry_point : str
        Entry point value in `"module:function"` format.
    package_name : str
        Package that provides this tag provider.
    """

    name: str
    entry_point: str
    package_name: str
