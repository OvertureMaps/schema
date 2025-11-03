"""
Metadata that can be attached to arbitrary Python values.

Overture Metadata is primarily used to supply metadata for code generation use cases.
"""

from collections.abc import (
    Hashable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    ValuesView,
)
from typing import (
    Union,
    cast,
    overload,
)

from typing_extensions import override


class Key:
    """
    Opaque, immutable, key into a `Metadata` dictionary.

    The purpose of `Key` is to allow metadata owners to minimize the probability of a collision
    between their module's metadata and some foreign module's metadata.

    Parameters
    ----------
    name : str
        Name of the metadata key.

        📌 As a best practice, set `name` to the fully-qualified name of the Python module or
        class that owns your metadata, *e.g.* `mypkg.mymodule` or `mypkg.mymodule.MyClass`.
    private: Hashable | None
        Opaque private data to reduce the changes of key collisions.

        📌 As a best practice, use a type value that is private to your module as the value for
        `private`.

    Attributes
    ----------
    name : str
        Name of the metadata key

    Example
    -------
    >>> class _private: pass    # Private data
    >>>
    >>> Key('mypkg.mymodule', _private)
    Key('mypkg.mymodule', ...)
    """

    __slots__ = ("name", "_Key__private")

    name: str
    __private: Hashable | None

    def __init__(self, name: str, private: Hashable | None = None) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "_Key__private", private)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Key):
            return self.name == other.name and self.__private == other.__private
        return False

    def __hash__(self) -> int:
        return hash((self.name, self.__private))

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Key({repr(self.name)}, ...)"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("cannot modify a `Key`")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("cannot modify a `Key`")


_METADATA_PRIVATE_KEY_NAME = "_[overture.system.system.Metadata]__private_key"


class Metadata(MutableMapping[Key, object]):
    """
    Metadata dictionary that can be attached to an arbitrary Python value.

    The Overture schema system attaches uses metadata attached to Pydantic model classes to
    register model-level constraints. The metadata system is fully reusable and can be used to
    attach your own custom metadata to your models as well.

    A `Metadata` instance behaves like a specialization of `dict` where the key type is always an
    instance of `Key`.

    Parameters
    ----------
    data : Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None
        Source data to build the `Metadata` dictionary

    Examples
    --------
    Create some metadata:

    >>> key = Key('mypkg.mymodule')
    >>> metadata = Metadata({key: 42})

    Attach the metadata to a class and retrieve it again:

    >>> class Foo: pass
    >>> metadata.copy().attach_to(Foo)
    >>> Metadata.retrieve_from(Foo)
    Metadata({Key('mypkg.mymodule', ...): 42})

    Attach the metadata to an instance of a class and retrieve it again:

    >>> class Bar: pass
    >>> bar = Bar()
    >>> metadata.copy().attach_to(bar)
    >>> Metadata.retrieve_from(bar)
    Metadata({Key('mypkg.mymodule', ...): 42})
    """

    __slots__ = "_Metadata__wrapped"

    def __init__(
        self,
        data: Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None,
    ):
        if not data:
            self.__wrapped = {}
        else:
            self.__wrapped = dict(Metadata.__validate_data(data))

    def __str__(self) -> str:
        return str(self.__wrapped)

    def __repr__(self) -> str:
        if len(self.__wrapped) > 0:
            return f"Metadata({repr(self.__wrapped)})"
        else:
            return "Metadata()"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Metadata):
            return self.__wrapped == other.__wrapped
        elif isinstance(other, Mapping):
            return self.__wrapped == other
        else:
            return False

    def __len__(self) -> int:
        return len(self.__wrapped)

    def __getitem__(self, key: Key) -> object:
        return self.__wrapped[key]

    def __iter__(self) -> Iterator[Key]:
        return iter(self.__wrapped)

    def __contains__(self, key: object) -> bool:
        return key in self.__wrapped

    def __delitem__(self, key: Key) -> None:
        del self.__wrapped[key]

    def __setitem__(self, key: Key, value: object) -> None:
        if not isinstance(key, Key):
            raise TypeError(
                f"key must be a `Key`, but {key} has type `{type(key).__name__}`"
            )
        self.__wrapped.__setitem__(key, value)

    def __ior__(
        self, other: Mapping[Key, object] | Iterable[tuple[Key, object]]
    ) -> "Metadata":
        self.update(other)
        return self

    def __or__(
        self, other: Mapping[Key, object] | Iterable[tuple[Key, object]]
    ) -> "Metadata":
        result = Metadata(self)
        result.update(other)
        return result

    def __ror__(
        self, other: Mapping[Key, object] | Iterable[tuple[Key, object]]
    ) -> "Metadata":
        result = Metadata(other)
        result.update(self)
        return result

    @override
    def get(self, key: Key, default: object = None) -> object:
        return self.__wrapped.get(key, default)

    @override
    def keys(self) -> KeysView[Key]:
        return self.__wrapped.keys()

    @override
    def values(self) -> ValuesView[object]:
        return self.__wrapped.values()

    @override
    def items(self) -> ItemsView[Key, object]:
        return self.__wrapped.items()

    def copy(self) -> "Metadata":
        """
        Return a shallow copy of this metadata.
        """
        return Metadata(self.__wrapped.copy())

    @overload  # type: ignore[override]
    def update(self, other: Mapping[Key, object], /) -> None: ...

    @overload
    def update(self, other: Iterable[tuple[Key, object]], /) -> None: ...

    def update(
        self,
        data: Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None,
    ) -> None:
        """
        Update this metadata by inserting values from `data`. In the case of a key conflict, the new
        value from `data` replaces the old value.

        Parameters
        ----------
        data : Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None
            New data to insert (ignored if the value is `None`)
        """
        if data:
            self.__wrapped.update(Metadata.__validate_data(data))

    def attach_to(self, target: object) -> None:
        """
        Attach this metadata to the given target value. The metadata can be retrieved by calling
        `retrieve_from`.

        Parameters
        ----------
        target : object
            Value to attach this metadata to

        Raises
        ------
        AttributeError
            If `target` will not accept new attributes, which can happen if it is a builtin type or
            value, a frozen value, *etc.*
        """
        setattr(target, _METADATA_PRIVATE_KEY_NAME, self)

    @staticmethod
    def retrieve_from(
        source: object,
        default: Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None,
    ) -> Union["Metadata", None]:
        """
        Retrieve the metadata attached go a given source value, if it exists. Metadata can be
        attached by calling `attach_to`.

        Parameters
        ----------
        source : object
            Value to retrieve the metadata from
        default : default: Mapping[Key, object] | Iterable[tuple[Key, object]] | None = None
            Default value to return if `source` has no attached metadata

        Returns
        -------
        Union["Metadata", None]
            The metadata attached to `source`, if it exists, or `default` otherwise
        """
        maybe_metadata = getattr(source, _METADATA_PRIVATE_KEY_NAME, None)
        if not maybe_metadata and default is None:
            return None
        elif not maybe_metadata:
            return Metadata(default)
        elif not isinstance(maybe_metadata, Metadata):
            raise TypeError(
                f"attribute {_METADATA_PRIVATE_KEY_NAME} must be a `Metadata` instance, but {maybe_metadata} has type `{type(maybe_metadata).__name__}`"
            )
        else:
            return cast(Metadata, maybe_metadata)

    @staticmethod
    def __validate_data(
        data: Mapping[Key, object] | Iterable[tuple[Key, object]],
    ) -> Mapping[Key, object] | Iterable[tuple[Key, object]]:
        if isinstance(data, Mapping):
            for k, _ in data.items():
                if not isinstance(k, Key):
                    raise TypeError(
                        f"key must be a `Key`, but {k} has type `{type(k).__name__}`"
                    )
        elif isinstance(data, Iterable):
            for i, item in enumerate(data):
                if not isinstance(item, (tuple, list)):
                    raise TypeError(
                        f"items must be pairs (`tuple` or `list`), but item index {i} has type `{type(item).__name__}`"
                    )
                elif len(item) != 2:
                    raise ValueError(
                        f"items must be pairs, but item index {i} has len = {len(item)}"
                    )
                elif not isinstance(item[0], Key):
                    raise TypeError(
                        f"each item's first element must be a `Key`, but first element for item index {i} has type `{type(item[0]).__name__}`"
                    )
            return cast(Iterable[tuple[Key, object]], data)
        else:
            raise TypeError(
                f"`data` must be a `Mapping` or `Iterable`, but {data} has type `{type(data).__name__}`"
            )
        return data
