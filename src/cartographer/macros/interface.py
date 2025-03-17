from __future__ import annotations

from typing import Protocol


class MacroParams(Protocol):
    def get(self, name: str, default: str = ...) -> str: ...
    def get_float(self, name: str, default: float = ..., *, above: int = ...) -> float: ...
    def get_int(self, name: str, default: int = ..., *, minval: int = ...) -> int: ...


class Macro(Protocol):
    name: str
    description: str

    def run(self, params: MacroParams) -> None: ...
