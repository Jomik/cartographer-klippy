from __future__ import annotations

import logging
from typing import Optional, final

from configfile import ConfigWrapper
from extras import probe
from gcode import GCodeCommand
from typing_extensions import override

from cartographer.endstop import ScannerEndstopWrapper
from cartographer.mcu import ScannerMCUHelper
from cartographer.stream_handler import StreamHandler


@final
class PrinterScanner:
    def __init__(self, config: ConfigWrapper):
        printer = config.get_printer()
        mcu_helper = ScannerMCUHelper(config)
        stream_handler = StreamHandler(printer, mcu_helper)
        endstop = ScannerEndstopWrapper(config, mcu_helper, stream_handler)
        probe_interface = ScannerProbe(config, endstop)
        printer.add_object("probe", probe_interface)
        logging.info("Successfully added probe!")


@final
class ScannerProbe(probe.PrinterProbe):
    def __init__(self, config: ConfigWrapper, endstop: ScannerEndstopWrapper):
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
