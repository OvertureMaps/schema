from enum import Enum
from types import NoneType, UnionType
from typing import Annotated, Any, Generic, TypeVar, Union, get_args, get_origin

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

T = TypeVar("T")


class Omitable(Generic[T]):
    """
    Type hint representing a value that can be omitted.

    Use this type in preference to `None` if you need your Pydantic model to use JSON Schema
    optionality semantics instead of Pydantic optionality semantics.

    By default, Pydantic conflates "not there" with "nullable" when generating JSON Schemas. This
    means that a field that is marked as optional using the standard Pydantic approach of creating a
    union with `None` will get a JSON Schema that is the union of the JSON Schema `null` type with
    the main type, for example:

    >>> from pydantic import BaseModel
    >>>
    >>> class MyModel(BaseModel):
    ...     my_optional_field: int | None = None
    ...
    >>> MyModel().model_dump()
    {'my_optional_field': None}
    >>> json_schema = MyModel.model_json_schema()
    >>> json_schema['properties']['my_optional_field']['anyOf']
    [{'type': 'integer'}, {'type': 'null'}]

    Although this approach works well in many scenarios, it can't represent JSON Schemas that allow
    values to be omitted but do not allow them to be explicitly set to the JSON value `null`, for
    example a schema such as:

    ```json
    {
      "type": "object",
      "required": ["foo"],
      "properties": {
        "foo": {
          "type": "string"
        },
        "bar": {
          "type": "integer"
        }
      }
    }
    ```

    In the above JSON Schema, the property `"bar"` is allowed to be omitted, but if present it must
    be an integer. Under no circumstances can it contain the value `null`. The `Omitable` type
    allows this to be modeled in Pydantic:

    >>> from pydantic import BaseModel
    >>> class MyModel(BaseModel):
    ...     foo: str
    ...     bar: Omitable[int]
    >>> json_schema = MyModel.model_json_schema()
    >>> bar_type = json_schema['properties']['bar']['type']
    >>> assert 'integer' == bar_type
    """

    def __class_getitem__(cls, item: Any) -> Any:
        if _has_none(item):
            raise TypeError(
                f"`None` not allowed in `{Omitable.__name__}` args, but found `None` in {item}"
            )
        return Annotated[item | MISSING, Field(default=MISSING)]


# todo - Vic - finish this
class Optionality(str, Enum):
    # This is for implementing the model constraints more cleverly.
    #       Noneable -> It is allowed to be `null` in JSON Schema.
    #                   To make it @required, need to take away the right to set `null`.
    #
    #
    OMITABLE = ("omitable",)
    NONEABLE = ("noneable",)
    NOT_OPTIONAL = ("not_optional",)


def _has_none(value: Any) -> bool:
    if value is None or value is NoneType:
        return True
    origin = get_origin(value)
    if origin is Annotated:
        return _has_none(get_args(value)[0])
    elif get_origin(value) in (Union, UnionType):
        args = get_args(value)
        return any(_has_none(a) for a in args)
    else:
        return False
