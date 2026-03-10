from overture.schema.system.discovery import tags_by_key, tags_by_namespace

def test_tags_by_key_returns_correct_values() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "overture:theme"
    result = tags_by_key(tags, key)
    assert result == {"buildings"}

def test_tags_by_key_returns_empty_set_for_nonexistent_key() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "nonexistent:key"
    result = tags_by_key(tags, key)
    assert result == set()

def test_tags_by_key_handles_empty_tags() -> None:
    tags: frozenset[str] = frozenset()
    key = "overture:theme"
    result = tags_by_key(tags, key)
    assert result == set()

def test_tags_by_namespace_returns_correct_values() -> None:
    tags = frozenset({"system:extension", "overture"})
    namespace = "system"
    result = tags_by_namespace(tags, namespace)
    assert result == {"extension"}

def test_tags_by_namespace_returns_empty_set_for_nonexistent_namespace() -> None:
    tags = frozenset({"system:extension", "overture"})
    namespace = "nonexistent"
    result = tags_by_namespace(tags, namespace)
    assert result == set()

def test_tags_by_namespace_handles_empty_tags() -> None:
    tags: frozenset[str] = frozenset()
    namespace = "system"
    result = tags_by_namespace(tags, namespace)
    assert result == set()
