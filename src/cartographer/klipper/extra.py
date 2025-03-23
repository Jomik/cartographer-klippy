from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from cartographer.endstops import ScanEndstop
from cartographer.klipper.configuration import KlipperCartographerConfiguration
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.logging import GCodeConsoleFormatter, GCodeConsoleHandler, apply_logging_config
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.macros import ProbeAccuracyMacro, ProbeMacro
from cartographer.macros.probe import QueryProbe, ZOffsetApplyProbe
from cartographer.probes import ScanModel, ScanProbe

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.printer_interface import Macro

logger = logging.getLogger(__name__)


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


apply_logging_config()


@final
class PrinterCartographer:
    config: KlipperCartographerConfiguration

    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()
        logger.debug("Initializing Cartographer")
        self.config = KlipperCartographerConfiguration(config)

        model = ScanModel(self.config.scan_models["default"])

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
        macro_logger.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)

        handler = GCodeConsoleHandler(self.gcode)
        handler.setFormatter(GCodeConsoleFormatter())

        macro_logger.addHandler(handler)
