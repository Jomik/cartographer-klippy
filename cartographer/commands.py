from __future__ import annotations

from typing import Callable, final

from gcode import GCodeCommand
from klippy import Printer

from cartographer.helpers.strings import cleandoc
from cartographer.scan.endstop import ScanEndstop
from cartographer.scan.mesh.helper import ScanMeshHelper

_CommandHandler = Callable[[GCodeCommand], None]

command_registry: dict[str, Callable[[CartographerCommands, GCodeCommand], None]] = {}
command_override_registry: dict[
    str, Callable[[CartographerCommands, GCodeCommand, _CommandHandler], None]
] = {}


def register_command(name: str):
    def decorator(
        func: Callable[[CartographerCommands, GCodeCommand], None],
    ) -> Callable[[CartographerCommands, GCodeCommand], None]:
        # Store the function in the global registry with its command name
        command_registry[name] = func
        return func

    return decorator


def register_command_override(name: str):
    def decorator(
        func: Callable[[CartographerCommands, GCodeCommand, _CommandHandler], None],
    ) -> Callable[[CartographerCommands, GCodeCommand, _CommandHandler], None]:
        # Store the function in the global registry with its command name
        command_override_registry[name] = func
        return func

    return decorator


@final
class CartographerCommands:
    def __init__(
        self,
        printer: Printer,
        endstop: ScanEndstop,
        mesh_helper: ScanMeshHelper,
    ) -> None:
        self._printer = printer
        self._endstop = endstop
        self._mesh_helper = mesh_helper

        self._register_decorated_commands()

    def _register_decorated_commands(self) -> None:
        gcode = self._printer.lookup_object("gcode")
        for name, func in command_registry.items():
            gcode.register_command(
                name,
                lambda gcmd: func(self, gcmd),
                desc=cleandoc(func.__doc__),
            )

        for name, func_override in command_override_registry.items():
            old = gcode.register_command(name, None)
            if old is None:
                raise self._printer.config_error(f"Command {name} does not exist")
            old_handler = old
            gcode.register_command(
                name,
                lambda gcmd: func_override(self, gcmd, old_handler),
                desc=cleandoc(func_override.__doc__),
            )

    @register_command("PROBE_CALIBRATE")
    def cmd_PROBE_CALIBRATE(self, gcmd: GCodeCommand) -> None:
        """
        Calibrate the probe's z-offset and cartographer's response curve
        """
        self._endstop.start_calibration(gcmd)

    @register_command("PROBE_ACCURACY")
    def cmd_PROBE_ACCURACY(self, gcmd: GCodeCommand) -> None:
        """
        Measure the probe's accuracy
        """
        self._endstop.measure_accuracy(gcmd)

    @register_command_override("BED_MESH_CALIBRATE")
    def cmd_BED_MESH_CALIBRATE(
        self, gcmd: GCodeCommand, old_handler: _CommandHandler
    ) -> None:
        """
        Perform Mesh Bed Leveling
        """
        # TODO: Validate METHOD
        if gcmd.get("METHOD", "").upper() != "SCAN":
            return old_handler(gcmd)

        self._mesh_helper.calibrate(gcmd)
