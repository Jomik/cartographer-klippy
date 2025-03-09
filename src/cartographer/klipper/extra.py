from __future__ import annotations

from typing import TYPE_CHECKING, final

from cartographer.endstops import ScanEndstop
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.temperature import PrinterTemperatureCoil

if TYPE_CHECKING:
    from configfile import ConfigWrapper


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()

        self.mcu = KlipperCartographerMcu(config)
        toolhead = KlipperToolhead(config)
        endstop = KlipperEndstop(self.mcu, ScanEndstop(toolhead, self.mcu, model=None))
        homing_chip = CartographerHomingChip(printer, endstop)

        config.get_printer().lookup_object("pins").register_chip("cartographer", homing_chip)
