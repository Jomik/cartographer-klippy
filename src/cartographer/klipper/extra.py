from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from cartographer.endstops import ScanEndstop
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.logging import GCodeConsoleFormatter, GCodeConsoleHandler, apply_logging_config
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.macros import Macro, ProbeAccuracyMacro, ProbeMacro
from cartographer.macros.probe import QueryProbe, ZOffsetApplyProbe
from cartographer.model import Boundary, Model
from cartographer.probes import ScanProbe

if TYPE_CHECKING:
    from configfile import ConfigWrapper

logger = logging.getLogger(__name__)


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

apply_logging_config()


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()
        logger.debug("Initializing Cartographer")

        model = Model.from_coefficients(coefficients, domain, z_range)

        self.mcu = KlipperCartographerMcu(config)
        toolhead = KlipperToolhead(config)
        scan_probe = ScanProbe(self.mcu, toolhead, model=model)
        scan_endstop = ScanEndstop(self.mcu, scan_probe)

        endstop = KlipperEndstop(self.mcu, scan_endstop)
        homing_chip = CartographerHomingChip(printer, endstop)

        config.get_printer().lookup_object("pins").register_chip("probe", homing_chip)

        self.gcode = printer.lookup_object("gcode")
        self._configure_macro_logger()
        self._register_macro(ProbeMacro(scan_probe))
        self._register_macro(ProbeAccuracyMacro(scan_probe, toolhead))
        self._register_macro(QueryProbe(scan_endstop, toolhead))
        self._register_macro(ZOffsetApplyProbe(toolhead))

    def _register_macro(self, macro: Macro) -> None:
        self.gcode.register_command(macro.name, macro.run, desc=macro.description)

    def _configure_macro_logger(self) -> None:
        macro_logger = logging.getLogger("cartographer.macros")
        # TODO: Configure from configfile
        macro_logger.setLevel(logging.DEBUG)

        handler = GCodeConsoleHandler(self.gcode)
        handler.setFormatter(GCodeConsoleFormatter())

        macro_logger.addHandler(handler)
