from __future__ import annotations

from typing import Callable, final

from gcode import GCodeCommand
from klippy import Printer

from cartographer.helpers.strings import cleandoc


from cartographer.scan.endstop import ScanEndstop

command_registry: dict[str, Callable[[CartographerCommands, GCodeCommand], None]] = {}


def register_command(name: str):
    def decorator(
        func: Callable[[CartographerCommands, GCodeCommand], None],
    ) -> Callable[[CartographerCommands, GCodeCommand], None]:
        # Store the function in the global registry with its command name
        command_registry[name] = func
        return func

    return decorator


@final
class CartographerCommands:
    def __init__(
        self,
        printer: Printer,
        endstop: ScanEndstop,
    ) -> None:
        self._printer = printer
        self._endstop = endstop

        self._register_decorated_commands()

    def _register_decorated_commands(self) -> None:
        gcode = self._printer.lookup_object("gcode")
        for name, func in command_registry.items():
            gcode.register_command(
                name, lambda gcmd: func(self, gcmd), desc=cleandoc(func.__doc__)
            )

    @register_command("PROBE_CALIBRATE")
    def cmd_PROBE_CALIBRATE(self, gcmd: GCodeCommand) -> None:
        """
        Calibrate the probe's z-offset and the scanner's response curve
        """
        self._endstop.start_calibration(gcmd)

    @register_command("PROBE_ACCURACY")
    def cmd_PROBE_ACCURACY(self, gcmd: GCodeCommand) -> None:
        """
        Measure the probe's accuracy
        """
        self._endstop.measure_accuracy(gcmd)
