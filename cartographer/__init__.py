from __future__ import annotations

from typing import Optional, final

from configfile import ConfigWrapper
from extras import probe
from gcode import GCodeCommand
from typing_extensions import override

from .endstop.model import ScanModel
from .endstop.scan import ScanEndstop
from .endstop.wrapper import EndstopWrapper
from .mcu.helper import McuHelper
from .mcu.stream import StreamHandler


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper):
        printer = config.get_printer()
        mcu_helper = McuHelper(config)
        model = ScanModel.load(config, "default")
        self._stream_handler = StreamHandler(
            mcu_helper.get_mcu().get_printer(), mcu_helper
        )
        endstop = ScanEndstop(mcu_helper, model, self._stream_handler)
        endstop_wrapper = EndstopWrapper(config, mcu_helper, endstop)
        probe_interface = ProbeInterface(config, endstop_wrapper)
        printer.add_object("probe", probe_interface)

    def get_stream_handler(self) -> StreamHandler:
        return self._stream_handler


@final
class ProbeInterface(probe.PrinterProbe):
    def __init__(self, config: ConfigWrapper, endstop: EndstopWrapper):
        self.cmd_helper = probe.ProbeCommandHelper(config, self, endstop.query_endstop)
        self.probe_offsets = probe.ProbeOffsetsHelper(config)
        self.probe_session = probe.ProbeSessionHelper(config, endstop)

    @override
    def get_probe_params(self, gcmd: Optional[GCodeCommand] = None):
        return self.probe_session.get_probe_params(gcmd)

    @override
    def get_offsets(self):
        return self.probe_offsets.get_offsets()

    @override
    def get_status(self, eventtime: float):
        return self.cmd_helper.get_status(eventtime)

    @override
    def start_probe_session(self, gcmd: GCodeCommand):
        return self.probe_session.start_probe_session(gcmd)
