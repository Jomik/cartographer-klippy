from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from extras.probe import (
    HomingViaProbeHelper,
)

from cartographer.calibration.model import ScanModel
from cartographer.endstop.scan import ScanEndstop
from cartographer.endstop.wrapper import EndstopWrapper
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper):
        mcu_helper = McuHelper(config)
        model = ScanModel.load(config, "default")
        self._stream_handler = StreamHandler(
            mcu_helper.get_mcu().get_printer(), mcu_helper
        )
        endstop = ScanEndstop(mcu_helper, model, self._stream_handler)
        endstop_wrapper = EndstopWrapper(config, mcu_helper, endstop)
        _ = HomingViaProbeHelper(config, endstop_wrapper)

    def get_stream_handler(self) -> StreamHandler:
        return self._stream_handler
