from __future__ import annotations

from typing import TYPE_CHECKING, final

from cartographer.klipper.mcu import KlipperCartographerMcu
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
        self.mcu = KlipperCartographerMcu(config)
