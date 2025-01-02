from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from extras.probe import (
    HomingViaProbeHelper,
)

from cartographer.hardware_checks import HardwareObserver
from cartographer.scan.calibration.helper import CalibrationHelper
from cartographer.scan.calibration.model import Model
from cartographer.commands import CartographerCommands
from cartographer.configuration import CommonConfiguration
from cartographer.scan.endstop import ScanEndstop
from cartographer.endstop_wrapper import EndstopWrapper
from cartographer.logging_config import apply_logging_config
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper):
        printer = config.get_printer()
        common_config = CommonConfiguration(config)
        mcu_helper = McuHelper(common_config)
        self._stream_handler = StreamHandler(printer, mcu_helper)
        calibration_helper = CalibrationHelper(
            common_config, mcu_helper, self._stream_handler
        )

        model = Model.load(config, "default")
        endstop = ScanEndstop(mcu_helper, model, self._stream_handler)
        endstop_wrapper = EndstopWrapper(endstop)

        _ = HomingViaProbeHelper(config, endstop_wrapper)
        _ = CartographerCommands(printer, calibration_helper)
        _ = HardwareObserver(mcu_helper)

    def get_stream_handler(self) -> StreamHandler:
        return self._stream_handler


apply_logging_config()
