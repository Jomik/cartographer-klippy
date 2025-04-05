from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, final

import pins

if TYPE_CHECKING:
    from klippy import Printer
    from mcu import MCU_endstop


# https://github.com/Klipper3d/klipper/blob/75a10bfcafc0655e36e5ecf01c3f2033a14ef2c7/klippy/pins.py#L93-L94
class _PinParams(TypedDict):
    pin: str
    invert: int
    pullup: int


@final
class CartographerHomingChip:
    def __init__(self, printer: Printer, endstop: MCU_endstop) -> None:
        self.endstop = endstop

    def setup_pin(self, pin_type: str, pin_params: _PinParams) -> MCU_endstop:
        if pin_type != "endstop" or pin_params["pin"] != "z_virtual_endstop":
            msg = "cartographer virtual endstop only useful as endstop pin"
            raise pins.error(msg)
        if pin_params["invert"] or pin_params["pullup"]:
            msg = "can not pullup/invert probe virtual endstop"
            raise pins.error(msg)

        return self.endstop
