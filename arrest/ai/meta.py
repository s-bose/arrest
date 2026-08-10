from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ToolMeta:
    """Tool metadata for per-handler config overrides.

    Parameters:
        name (str, optional):
            overrides the auto-generated tool name. Defaults to None, in
            which case a name is derived from the resource, method, and route.
        description (str, optional):
            overrides the auto-generated tool description. Defaults to None,
            in which case a description is derived from the handler's method
            and route.
        include (bool, optional):
            whether this handler is registered as a tool at all. Defaults to True.
        strict (bool, optional):
            whether the tool should be invoked in strict mode. Defaults to
            None, which defers to the model/framework default.
        metadata (dict, optional):
            free-form metadata attached to the tool, for future use. Defaults to None.
        max_items (int, optional):
            maximum number of items returned before truncation kicks in.
            Only applies to list responses. Defaults to None (no truncation).
        on_truncate ("note" | "raise", optional):
            what happens when a response exceeds `max_items`: "note" returns
            a truncated payload annotated with truncation metadata; "raise"
            fails the tool call instead, prompting the model to narrow its
            query. Defaults to "note".
    """

    name: str | None = None
    description: str | None = None
    include: bool = True
    strict: bool | None = None
    metadata: dict[str, Any] | None = None
    max_items: int | None = None
    on_truncate: Literal["note", "raise"] = "note"
