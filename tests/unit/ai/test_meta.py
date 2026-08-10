import dataclasses

import pytest

from arrest.ai.meta import ToolMeta


def test_tool_meta_defaults():
    """Every field is optional, and the two defaults `ArrestToolset` branches
    on -- `include` and `on_truncate` -- are the permissive ones."""
    meta = ToolMeta()

    assert meta.name is None
    assert meta.description is None
    assert meta.include is True
    assert meta.strict is None
    assert meta.metadata is None
    assert meta.max_items is None
    assert meta.on_truncate == "note"


def test_tool_meta_is_frozen():
    meta = ToolMeta(name="get_user")

    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.name = "renamed"  # type: ignore[misc]
