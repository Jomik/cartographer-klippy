from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from klippy import Printer


@final
class CommonConfiguration:
    def __init__(self, config: ConfigWrapper) -> None:
        self._printer = config.get_printer()
        self.mcu_name = config.get("mcu")
        self.x_offset = config.getfloat("x_offset")
        self.y_offset = config.getfloat("y_offset")
        self.move_speed = config.getfloat("move_speed", 50.0)

    def get_printer(self) -> Printer:
        return self._printer
