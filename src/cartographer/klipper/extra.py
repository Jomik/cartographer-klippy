from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from cartographer.configuration import ProbeMode
from cartographer.klipper.configuration import KlipperCartographerConfiguration, KlipperProbeConfiguration
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.logging import setup_console_logger
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.probe import KlipperCartographerProbe
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.macros import ProbeAccuracyMacro, ProbeMacro, QueryProbeMacro, ZOffsetApplyProbeMacro
from cartographer.probes import ScanModel, ScanProbe, TouchProbe

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.printer_interface import Macro

logger = logging.getLogger(__name__)


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


@final
class PrinterCartographer:
    config: KlipperCartographerConfiguration

    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()
        logger.debug("Initializing Cartographer")
        self.config = KlipperCartographerConfiguration(config)

        probe_config = self.config.scan_models["default"]
        model = ScanModel(probe_config)

        self.mcu = KlipperCartographerMcu(config)
        toolhead = KlipperToolhead(config, self.mcu)

        scan_probe = ScanProbe(self.mcu, toolhead, model=model)
        scan_endstop = KlipperEndstop(self.mcu, scan_probe)

        touch_probe = TouchProbe(self.mcu, toolhead, threshold=2750)

        homing_chip = CartographerHomingChip(printer, scan_endstop)

        printer.lookup_object("pins").register_chip("probe", homing_chip)

        probing_probe = touch_probe if self.config.probing_mode is ProbeMode.TOUCH else scan_probe

        self.gcode = printer.lookup_object("gcode")
        self._configure_macro_logger()
        probe_macro = ProbeMacro(probing_probe)
        self._register_macro(probe_macro)
        self._register_macro(ProbeAccuracyMacro(probing_probe, toolhead))
        query_probe_macro = QueryProbeMacro(probing_probe, toolhead)
        self._register_macro(query_probe_macro)
        self._register_macro(ZOffsetApplyProbeMacro(toolhead))

        printer.add_object(
            "probe",
            KlipperCartographerProbe(
                scan_probe,
                KlipperProbeConfiguration(self.config, probe_config),
                probe_macro,
                query_probe_macro,
            ),
        )

    def _register_macro(self, macro: Macro) -> None:
        self.gcode.register_command(macro.name, macro.run, desc=macro.description)

    def _configure_macro_logger(self) -> None:
        handler = setup_console_logger(self.gcode)

        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        handler.setLevel(log_level)
