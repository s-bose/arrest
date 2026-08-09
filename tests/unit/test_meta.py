import dataclasses

import pytest

from arrest.ai.meta import ToolMeta


def test_tool_meta_requires_name_and_description():
    with pytest.raises(TypeError):
        ToolMeta()  # type: ignore
    with pytest.raises(TypeError):
        ToolMeta(name="get_user")  # type: ignore


def test_tool_meta_defaults():
    meta = ToolMeta(name="get_user", description="Fetch a user by id")

    assert meta.enabled is True
    assert meta.strict is None
    assert meta.timeout is None
    assert meta.metadata is None
    assert meta.max_items is None
    assert meta.on_truncate == "note"


def test_tool_meta_is_frozen():
    meta = ToolMeta(name="get_user", description="Fetch a user by id")

    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.name = "renamed"  # type: ignore[misc]
