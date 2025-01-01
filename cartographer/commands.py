from typing import Callable, final

from gcode import GCodeCommand
from klippy import Printer

from cartographer.calibration.helper import CalibrationHelper
from cartographer.helpers.strings import cleandoc


@final
class CartographerCommands:
    def __init__(self, printer: Printer, calibration_helper: CalibrationHelper):
        self._printer = printer
        self._gcode = printer.lookup_object("gcode")
        self._calibration_helper = calibration_helper
        self._register_command("PROBE_CALIBRATE", self.cmd_PROBE_CALIBRATE)

    def _register_command(
        self, name: str, func: Callable[[GCodeCommand], None]
    ) -> None:
        self._gcode.register_command(name, func, desc=cleandoc(func.__doc__))

    def cmd_PROBE_CALIBRATE(self, gcmd: GCodeCommand) -> None:
        """
        Calibrate the probe's z-offset and the scanner's response curve
        """
        self._calibration_helper.start_calibration(gcmd)
