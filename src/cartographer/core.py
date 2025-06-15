from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from cartographer.macros.axis_twist_compensation import AxisTwistCompensationMacro
from cartographer.macros.backlash import EstimateBacklashMacro
from cartographer.macros.bed_mesh.scan_mesh import BedMeshCalibrateConfiguration, BedMeshCalibrateMacro
from cartographer.macros.probe import ProbeAccuracyMacro, ProbeMacro, QueryProbeMacro, ZOffsetApplyProbeMacro
from cartographer.macros.scan_calibrate import DEFAULT_SCAN_MODEL_NAME, ScanCalibrateMacro
from cartographer.macros.touch import TouchAccuracyMacro, TouchHomeMacro, TouchMacro
from cartographer.macros.touch_calibrate import DEFAULT_TOUCH_MODEL_NAME, TouchCalibrateMacro
from cartographer.probe.probe import Probe
from cartographer.probe.scan_mode import ScanMode, ScanModeConfiguration
from cartographer.probe.touch_mode import TouchMode, TouchModeConfiguration
from cartographer.toolhead import BacklashCompensatingToolhead

if TYPE_CHECKING:
    from cartographer.interfaces.printer import Macro
    from cartographer.runtime.adapters import Adapters

logger = logging.getLogger(__name__)


@final
class PrinterCartographer:
    def __init__(self, adapters: Adapters) -> None:
        self.mcu = adapters.mcu
        config = adapters.config
        toolhead = (
            BacklashCompensatingToolhead(adapters.toolhead, config.general.z_backlash)
            if config.general.z_backlash > 0
            else adapters.toolhead
        )

        self.scan_mode = ScanMode(
            self.mcu,
            toolhead,
            ScanModeConfiguration.from_config(config),
        )
        if DEFAULT_SCAN_MODEL_NAME in adapters.config.scan.models:
            self.scan_mode.load_model(DEFAULT_SCAN_MODEL_NAME)

        self.touch_mode = TouchMode(self.mcu, toolhead, TouchModeConfiguration.from_config(config))
        if DEFAULT_TOUCH_MODEL_NAME in adapters.config.touch.models:
            self.touch_mode.load_model(DEFAULT_TOUCH_MODEL_NAME)

        probe = Probe(self.scan_mode, self.touch_mode)

        self.macros: list[Macro] = [
            ProbeMacro(probe),
            ProbeAccuracyMacro(probe, toolhead),
            QueryProbeMacro(probe),
            ZOffsetApplyProbeMacro(probe, toolhead, config),
            TouchCalibrateMacro(probe, self.mcu, toolhead, config),
            TouchMacro(self.touch_mode),
            TouchAccuracyMacro(self.touch_mode, toolhead),
            TouchHomeMacro(self.touch_mode, toolhead, config.bed_mesh.zero_reference_position),
            BedMeshCalibrateMacro(
                probe,
                toolhead,
                adapters.bed_mesh,
                adapters.task_executor,
                BedMeshCalibrateConfiguration.from_config(config),
            ),
            ScanCalibrateMacro(probe, toolhead, config),
            EstimateBacklashMacro(toolhead, self.scan_mode, config),
        ]

        if adapters.axis_twist_compensation:
            self.macros.append(AxisTwistCompensationMacro(probe, toolhead, adapters.axis_twist_compensation, config))

    def get_status(self, eventtime: float) -> object:
        return {
            "scan": self.scan_mode.get_status(eventtime),
            "touch": self.touch_mode.get_status(eventtime),
        }
