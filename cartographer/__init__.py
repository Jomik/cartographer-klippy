from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from extras.probe import (
    HomingViaProbeHelper,
)

from cartographer.calibration.helper import CalibrationHelper
from cartographer.calibration.model import ScanModel
from cartographer.commands import CartographerCommands
from cartographer.configuration import CommonConfiguration
from cartographer.endstop.scan import ScanEndstop
from cartographer.endstop.wrapper import EndstopWrapper
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper):
        common_config = CommonConfiguration(config)
        mcu_helper = McuHelper(common_config)
        model = ScanModel.load(config, "default")
        printer = config.get_printer()
        self._stream_handler = StreamHandler(
            mcu_helper.get_mcu().get_printer(), mcu_helper
        )
        endstop = ScanEndstop(mcu_helper, model, self._stream_handler)
        endstop_wrapper = EndstopWrapper(mcu_helper, endstop)
        calibration_helper = CalibrationHelper(
            common_config, mcu_helper, self._stream_handler
        )
        _ = HomingViaProbeHelper(config, endstop_wrapper)
        _ = CartographerCommands(printer, calibration_helper)

    def get_stream_handler(self) -> StreamHandler:
        return self._stream_handler
