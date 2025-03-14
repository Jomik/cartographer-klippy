from __future__ import annotations

from typing import TYPE_CHECKING, final

from cartographer.endstops import ScanEndstop
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.model import Boundary, Model

if TYPE_CHECKING:
    from configfile import ConfigWrapper


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


coefficients = [
    1.495489734476631,
    1.818884970732857,
    0.7167873060601451,
    0.22706698538067396,
    0.47250958126556464,
    0.7893292346615394,
    0.3691949811150437,
    0.8464623041312073,
    0.33346414135574437,
    0.46140861763722246,
]
domain = Boundary(3.2110630714271213e-07, 3.343269852974841e-07)
z_range = Boundary(0.200000, 5.100000)


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()

        model = Model.from_coefficients(coefficients, domain, z_range)

        self.mcu = KlipperCartographerMcu(config)
        toolhead = KlipperToolhead(config)
        endstop = KlipperEndstop(self.mcu, ScanEndstop(toolhead, self.mcu, model))
        homing_chip = CartographerHomingChip(printer, endstop)

        config.get_printer().lookup_object("pins").register_chip("cartographer", homing_chip)
