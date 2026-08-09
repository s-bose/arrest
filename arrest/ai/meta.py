from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ToolMeta:
    name: str
    description: str
    enabled: bool = True
    strict: bool | None = None
    timeout: float | None = None
    metadata: dict[str, Any] | None = None
    max_items: int | None = None
    on_truncate: Literal["note", "raise"] = "note"
