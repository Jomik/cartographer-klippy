from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, final

from cartographer.klipper.bed_mesh import KlipperMeshConfiguration, KlipperMeshHelper
from cartographer.klipper.configuration import KlipperCartographerConfiguration
from cartographer.klipper.endstop import KlipperEndstop
from cartographer.klipper.homing import CartographerHomingChip
from cartographer.klipper.logging import setup_console_logger
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.klipper.mcu.mcu import Sample
from cartographer.klipper.printer import KlipperToolhead
from cartographer.klipper.probe import KlipperCartographerProbe
from cartographer.klipper.temperature import PrinterTemperatureCoil
from cartographer.lib.alpha_beta_filter import AlphaBetaFilter
from cartographer.macros import ProbeAccuracyMacro, ProbeMacro, QueryProbeMacro, ZOffsetApplyProbeMacro
from cartographer.macros.bed_mesh import BedMeshCalibrateMacro
from cartographer.macros.touch import TouchAccuracyMacro, TouchHomeMacro, TouchMacro
from cartographer.probes import ScanModel, ScanProbe, TouchProbe

if TYPE_CHECKING:
    from configfile import ConfigWrapper
    from gcode import GCodeCommand

    from cartographer.printer_interface import Macro

logger = logging.getLogger(__name__)


def load_config(config: ConfigWrapper):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("cartographer_coil", PrinterTemperatureCoil)
    return PrinterCartographer(config)


def smooth_with(filter: AlphaBetaFilter) -> Callable[[Sample], Sample]:
    def fn(sample: Sample) -> Sample:
        return Sample(
            sample.time,
            filter.update(measurement=sample.frequency, time=sample.time),
            sample.temperature,
        )

    return fn


@final
class PrinterCartographer:
    config: KlipperCartographerConfiguration

    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()
        logger.debug("Initializing Cartographer")
        self.config = KlipperCartographerConfiguration(config)

        filter = AlphaBetaFilter()
        self.mcu = KlipperCartographerMcu(config, smooth_with(filter))

        toolhead = KlipperToolhead(config, self.mcu)

        scan_config = self.config.scan_models["default"]
        model = ScanModel(scan_config)
        scan_probe = ScanProbe(self.mcu, toolhead, self.config, model=model)
        scan_endstop = KlipperEndstop(self.mcu, scan_probe)

        touch_config = self.config.touch_models["default"]
        touch_probe = TouchProbe(self.mcu, toolhead, self.config, model=touch_config)

        homing_chip = CartographerHomingChip(printer, scan_endstop)

        printer.lookup_object("pins").register_chip("probe", homing_chip)

        self.gcode = printer.lookup_object("gcode")
        self._configure_macro_logger()
        probe_macro = ProbeMacro(scan_probe)
        self._register_macro(probe_macro)
        self._register_macro(ProbeAccuracyMacro(scan_probe, toolhead))
        query_probe_macro = QueryProbeMacro(scan_probe, toolhead)
        self._register_macro(query_probe_macro)

        self._register_macro(ZOffsetApplyProbeMacro(toolhead))

        self._register_macro(TouchMacro(touch_probe))
        self._register_macro(TouchAccuracyMacro(touch_probe, toolhead))
        self._register_macro(TouchHomeMacro(touch_probe, toolhead))

        self._register_macro(
            BedMeshCalibrateMacro(
                scan_probe,
                toolhead,
                KlipperMeshHelper(config, self.gcode),
                KlipperMeshConfiguration.from_config(config, self.config),
            )
        )

        printer.add_object(
            "probe",
            KlipperCartographerProbe(
                scan_probe,
                probe_macro,
                query_probe_macro,
            ),
        )

    def _register_macro(self, macro: Macro[GCodeCommand]) -> None:
        self.gcode.register_command(macro.name, catch_macro_errors(macro.run), desc=macro.description)

    def _configure_macro_logger(self) -> None:
        handler = setup_console_logger(self.gcode)

        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        handler.setLevel(log_level)


def catch_macro_errors(func: Callable[[GCodeCommand], None]) -> Callable[[GCodeCommand], None]:
    def wrapper(gcmd: GCodeCommand) -> None:
        try:
            return func(gcmd)
        except RuntimeError as e:
            raise gcmd.error(str(e)) from e

    return wrapper
