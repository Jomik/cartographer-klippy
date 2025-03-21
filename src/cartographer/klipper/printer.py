from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.printer import Endstop, HomingAxis, HomingState, Position, Toolhead

if TYPE_CHECKING:
    from collections.abc import Sequence

    from configfile import ConfigWrapper
    from extras.homing import Homing
    from toolhead import ToolHead as KlippyToolhead

logger = logging.getLogger(__name__)

axis_mapping: dict[HomingAxis, int] = {
    "x": 0,
    "y": 1,
    "z": 2,
}


def axis_to_index(axis: HomingAxis) -> int:
    return axis_mapping[axis]


@final
class KlipperHomingState(HomingState):
    def __init__(self, homing: Homing, endstops: Sequence[Endstop[object]]) -> None:
        self.homing = homing
        self.endstops = endstops

    @override
    def is_homing_z(self) -> bool:
        return axis_to_index("z") in self.homing.get_axes()

    @override
    def set_z_homed_position(self, position: float) -> None:
        logger.debug("setting homed distance for z to %.2F", position)
        self.homing.set_homed_position([None, None, position])


@final
class KlipperToolhead(Toolhead):
    __toolhead: KlippyToolhead | None = None

    @property
    def toolhead(self) -> KlippyToolhead:
        if self.__toolhead is None:
            self.__toolhead = self.printer.lookup_object("toolhead")
        return self.__toolhead

    def __init__(self, config: ConfigWrapper) -> None:
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
    def manual_move(
        self, *, x: float | None = None, y: float | None = None, z: float | None = None, speed: float
    ) -> None:
        self.toolhead.manual_move([x, y, z], speed=speed)

    @override
    def is_homed(self, axis: HomingAxis) -> bool:
        time = self.reactor.monotonic()
        return axis in self.toolhead.get_status(time)["homed_axes"]

    @override
    def get_gcode_z_offset(self) -> float:
        gcode_move = self.printer.lookup_object("gcode_move")
        return gcode_move.get_status()["homing_origin"].z
