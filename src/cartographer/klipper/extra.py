from __future__ import annotations

from typing import TYPE_CHECKING, final

from cartographer.endstop import Endstop
from cartographer.klipper.endstop import EndstopWrapper
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.modes.none_mode import NoneMode

if TYPE_CHECKING:
    from configfile import ConfigWrapper


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        self.mcu = KlipperCartographerMcu(config)
        endstop = Endstop(self.mcu, NoneMode())
        _ = EndstopWrapper(self.mcu, endstop)
