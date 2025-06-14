from __future__ import annotations

from typing import overload

from typing_extensions import override

from cartographer.interfaces.printer import MacroParams


class MockParams(MacroParams):
    def __init__(self) -> None:
        self.params: dict[str, str] = {}

    @override
    def get(self, name: str, default: str = ...) -> str:
        return str(self.params.get(name, default))

    @overload
    def get_float(
        self, name: str, default: float = ..., *, above: float = ..., minval: float = ..., maxval: float = ...
    ) -> float: ...
    @overload
    def get_float(
        self, name: str, default: None, *, above: float = ..., minval: float = ..., maxval: float = ...
    ) -> float | None: ...

    @override
    def get_float(
        self, name: str, default: float | None = ..., *, above: float = ..., minval: float = ..., maxval: float = ...
    ) -> float | None:
        opt = self.params.get(name, default)
        return float(opt) if opt is not None else None

    @override
    def get_int(self, name: str, default: int = ..., *, minval: int = ..., maxval: int = ...) -> int:
        return int(self.params.get(name, default))
