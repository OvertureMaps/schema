"""Tag format specification and utilities for Overture schema discovery.

Tags follow the pattern `[namespace:]predicate[=value]` and come in three forms:

- **Plain** — `feature`
- **Namespaced** — `system:extension`
- **Key/value** — `overture:theme=buildings`

`:` signals ownership and reservation — only the owning package may set tags in a
given namespace. `=` signals a dimension with a discrete value.
One level of each: no nested colons, no multiple `=` signs.

Tag matching is case-sensitive throughout.
"""

import re

TAG_PART = r"[a-z0-9][a-z0-9_.-]*"
VALUE = r"[a-zA-Z0-9_.-]+"
NAMESPACE_TAG = rf"{TAG_PART}:{TAG_PART}(?:={VALUE})?"
TAG = re.compile(rf"^(?:{TAG_PART}|{NAMESPACE_TAG})$")


def get_namespace(tag: str) -> str:
    """Extract the namespace prefix from a namespaced tag.

    Parameters
    ----------
    tag : str
        A valid tag string.

    Returns
    -------
    str
        The namespace prefix if the tag is a namespaced tag, otherwise `""`.

    Examples
    --------
    >>> get_namespace("overture:theme=buildings")
    'overture'
    """
    return tag.split(":")[0] if is_valid_tag(tag) and ":" in tag else ""


def get_values_for_key(tags: frozenset[str] | set[str], key: str) -> set[str]:
    """Extract values from key/value namespaced tags matching the given key.

    Parameters
    ----------
    tags : frozenset[str] or set[str]
        Tags to search.
    key : str
        Key to match, e.g. `"overture:theme"`.

    Returns
    -------
    set[str]
        Values of tags matching `key=<value>`.

    Examples
    --------
    >>> get_values_for_key(frozenset({"overture:theme=buildings", "overture"}), "overture:theme")
    {'buildings'}
    """
    prefix = key + "="
    return {tag[len(prefix) :] for tag in tags if tag.startswith(prefix)}


def is_valid_tag(tag: str) -> bool:
    """Check whether a string is a valid tag.

    A valid tag is a plain tag, a namespaced tag, or a key/value tag:

    - **Plain / namespace / predicate**: `[a-z0-9][a-z0-9_.-]*` —
      lowercase alphanumeric start, then alphanumeric, hyphens,
      underscores, or dots.
    - **Key/value**: `{namespace}:{predicate}=[a-zA-Z0-9_.-]+` — namespace and
      predicate as above; value is alphanumeric (upper and lower case),
      hyphens, underscores, or dots; must be non-empty.

    Parameters
    ----------
    tag : str
        String to validate.

    Returns
    -------
    bool
        `True` if `tag` matches the required format.

    Examples
    --------
    >>> is_valid_tag("feature")
    True
    >>> is_valid_tag("overture:theme=buildings")
    True
    >>> is_valid_tag("overture:theme=")
    False
    >>> is_valid_tag("Invalid")
    False
    """
    return bool(TAG.fullmatch(tag))
