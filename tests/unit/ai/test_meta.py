import dataclasses

import pytest

from arrest.ai.meta import ToolMeta


def test_tool_meta_all_fields_are_optional():
    meta = ToolMeta()
    assert meta.name is None
    assert meta.description is None


@pytest.mark.parametrize(
    "field, default",
    [
        ("name", None),
        ("description", None),
        ("include", True),
        ("strict", None),
        ("metadata", None),
        ("max_items", None),
        ("on_truncate", "note"),
    ],
)
def test_tool_meta_defaults(field: str, default: object):
    meta = ToolMeta()
    assert getattr(meta, field) == default


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "get_user"},
        {"description": "Fetch a user by id"},
        {"name": "get_user", "description": "Fetch a user by id"},
        {"include": False},
        {"strict": True},
        {"metadata": {"tag": "internal"}},
        {"max_items": 10},
        {"on_truncate": "raise"},
    ],
)
def test_tool_meta_accepts_partial_overrides(kwargs: dict):
    meta = ToolMeta(**kwargs)
    for key, value in kwargs.items():
        assert getattr(meta, key) == value


def test_tool_meta_is_frozen():
    meta = ToolMeta(name="get_user")

    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.name = "renamed"  # type: ignore[misc]
