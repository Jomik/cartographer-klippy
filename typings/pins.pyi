# https://github.com/Klipper3d/klipper/blob/master/klippy/pins.py

from typing import Protocol, TypedDict

from mcu import MCU_endstop

class error(Exception): ...

class _PinParams(TypedDict):
    chip: _Chip
    chip_name: str
    pin: str
    invert: int
    pullup: int

class _Chip(Protocol):
    def setup_pin(self, pin_type: str, pin_params: _PinParams) -> MCU_endstop: ...

class PrinterPins:
    error: type[error]
    def register_chip(self, chip_name: str, chip: _Chip) -> None: ...
