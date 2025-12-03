from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolResult:
    kind: str              # "text" | "table" | "json" | "chart"
    value: Any              # str / dict / list / etc
    preview: str            # 给 debug 用的短预览


ToolFn = Callable[..., ToolResult]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"tool not found: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())
