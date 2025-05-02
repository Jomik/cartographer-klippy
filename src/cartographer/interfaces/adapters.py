from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from cartographer.interfaces.configuration import Configuration
    from cartographer.interfaces.printer import Endstop, Mcu, Toolhead


class Adapters(Protocol):
    config: Configuration
    toolhead: Toolhead
    mcu: Mcu

    def register_endstop_pin(self, chip_name: str, pin: str, endstop: Endstop) -> None: ...
