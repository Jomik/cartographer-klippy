from __future__ import annotations

from typing import final

from configfile import ConfigWrapper
from extras.probe import HomingViaProbeHelper
from mcu import TriggerDispatch

from cartographer.commands import CartographerCommands
from cartographer.configuration import CommonConfiguration
from cartographer.endstop_wrapper import EndstopWrapper
from cartographer.hardware_checks import HardwareObserver
from cartographer.logging_config import apply_logging_config
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import StreamHandler
from cartographer.probe import CartograherPrinterProbe
from cartographer.scan.calibration.model import Model
from cartographer.scan.endstop import ScanEndstop

apply_logging_config()


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper):
        printer = config.get_printer()
        common_config = CommonConfiguration(config)
        mcu_helper = McuHelper(common_config)
        self._stream_handler = StreamHandler(printer, mcu_helper)

        model = Model.load(config, "default")
        dispatch = TriggerDispatch(mcu_helper.get_mcu())
        endstop = ScanEndstop(
            common_config, mcu_helper, model, self._stream_handler, dispatch
        )
        endstop_wrapper = EndstopWrapper(mcu_helper, endstop, dispatch)

        _ = HomingViaProbeHelper(config, endstop_wrapper)
        _ = CartographerCommands(printer, endstop)
        _ = HardwareObserver(mcu_helper)

        probe = CartograherPrinterProbe(common_config, printer, endstop)
        printer.add_object("probe", probe)

    def get_stream_handler(self) -> StreamHandler:
        return self._stream_handler
