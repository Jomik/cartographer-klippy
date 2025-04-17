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
from cartographer.macros.scan import ScanCalibrateMacro
from cartographer.macros.touch import TouchAccuracyMacro, TouchCalibrateMacro, TouchHomeMacro, TouchMacro
from cartographer.probe import Probe, ScanMode, ScanModel, TouchMode

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

        scan_config = self.config.scan_models.get("default")
        model = ScanModel(scan_config) if scan_config else None
        scan_mode = ScanMode(self.mcu, toolhead, self.config, model=model)
        scan_endstop = KlipperEndstop(self.mcu, scan_mode)

        touch_config = self.config.touch_models.get("default")
        touch_mode = TouchMode(self.mcu, toolhead, self.config, model=touch_config)
        probe = Probe(scan_mode, touch_mode)

        homing_chip = CartographerHomingChip(printer, scan_endstop)

        printer.lookup_object("pins").register_chip("probe", homing_chip)

        mesh_config = KlipperMeshConfiguration.from_config(config, self.config)

        self.gcode = printer.lookup_object("gcode")
        self._configure_macro_logger()
        probe_macro = ProbeMacro(probe)
        self._register_macro(probe_macro)
        self._register_macro(ProbeAccuracyMacro(probe, toolhead))
        query_probe_macro = QueryProbeMacro(probe)
        self._register_macro(query_probe_macro)

        self._register_macro(ZOffsetApplyProbeMacro(probe, toolhead))

        self._register_macro(TouchMacro(touch_mode))
        self._register_macro(TouchAccuracyMacro(touch_mode, toolhead))
        touch_home = TouchHomeMacro(touch_mode, toolhead, mesh_config.zero_reference_position)
        self._register_macro(touch_home)
        self.gcode.register_command(
            "CARTOGRAHPER_TOUCH", catch_macro_errors(touch_home.run), desc=touch_home.description
        )

        self._register_macro(
            BedMeshCalibrateMacro(
                scan_mode,
                toolhead,
                KlipperMeshHelper(config, self.gcode),
                mesh_config,
            )
        )

        self._register_macro(ScanCalibrateMacro(scan_mode, toolhead, self.config))
        self._register_macro(
            TouchCalibrateMacro(touch_mode, toolhead, self.config, mesh_config.zero_reference_position)
        )

        printer.add_object(
            "probe",
            KlipperCartographerProbe(
                toolhead,
                scan_mode,
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
