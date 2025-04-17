from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, final

from extras.manual_probe import ManualProbeHelper
from typing_extensions import override

from cartographer.klipper.endstop import KlipperEndstop
from cartographer.printer_interface import Endstop, HomingAxis, Position, Toolhead

if TYPE_CHECKING:
    from configfile import ConfigWrapper
    from reactor import ReactorCompletion
    from toolhead import ToolHead as KlippyToolhead

    from cartographer.klipper.mcu.mcu import KlipperCartographerMcu

logger = logging.getLogger(__name__)


@final
class KlipperToolhead(Toolhead):
    __toolhead: KlippyToolhead | None = None

    @property
    def toolhead(self) -> KlippyToolhead:
        if self.__toolhead is None:
            self.__toolhead = self.printer.lookup_object("toolhead")
        return self.__toolhead

    def __init__(self, config: ConfigWrapper, mcu: KlipperCartographerMcu) -> None:
        self.mcu = mcu
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.motion_report = self.printer.load_object(config, "motion_report")

    @override
    def get_last_move_time(self) -> float:
        return self.toolhead.get_last_move_time()

    @override
    def wait_moves(self) -> None:
        self.toolhead.wait_moves()

    @override
    def get_position(self) -> Position:
        pos = self.toolhead.get_position()
        return Position(x=pos[0], y=pos[1], z=pos[2])

    @override
    def get_requested_position(self, time: float) -> Position:
        trapq = self.motion_report.trapqs.get("toolhead")
        if trapq is None:
            msg = "no dump trapq for toolhead"
            raise RuntimeError(msg)
        position, _ = trapq.get_trapq_position(time)
        if position is None:
            msg = f"no position for time {time}"
            raise RuntimeError(msg)
        return Position(x=position[0], y=position[1], z=position[2])

    @override
    def move(self, *, x: float | None = None, y: float | None = None, z: float | None = None, speed: float) -> None:
        self.toolhead.manual_move([x, y, z], speed=speed)

    @override
    def is_homed(self, axis: HomingAxis) -> bool:
        time = self.reactor.monotonic()
        return axis in self.toolhead.get_status(time)["homed_axes"]

    @override
    def get_gcode_z_offset(self) -> float:
        gcode_move = self.printer.lookup_object("gcode_move")
        return gcode_move.get_status()["homing_origin"].z

    @override
    # TODO: Fix override
    def z_homing_move(self, endstop: Endstop[ReactorCompletion], *, bottom: float, speed: float) -> float:  # pyright: ignore[reportIncompatibleMethodOverride]
        klipper_endstop = KlipperEndstop(self.mcu, endstop)
        self.wait_moves()

        pos = self.toolhead.get_position()[:]
        pos[2] = bottom

        epos = self.printer.lookup_object("homing").probing_move(klipper_endstop, pos, speed)
        return epos[2]

    @override
    def set_z_position(self, z: float) -> None:
        pos = self.toolhead.get_position()[:]
        pos[2] = z
        self.toolhead.set_position(pos, "z")

    @override
    def get_z_axis_limits(self) -> tuple[float, float]:
        time = self.toolhead.get_last_move_time()
        status = self.toolhead.get_status(time)
        return status["axis_minimum"][2], status["axis_maximum"][2]

    @override
    def manual_probe(self, finalize_callback: Callable[[Position | None], None]) -> None:
        gcode = self.printer.lookup_object("gcode")
        gcmd = gcode.create_gcode_command("", "", {})
        _ = ManualProbeHelper(
            self.printer,
            gcmd,
            lambda pos: finalize_callback(Position(pos[0], pos[1], pos[2]) if pos else None),
        )

    @override
    def clear_z_homing_state(self) -> None:
        self.toolhead.get_kinematics().clear_homing_state("z")

    @override
    def dwell(self, seconds: float) -> None:
        self.toolhead.dwell(seconds)
