from __future__ import annotations

from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.printer import HomingAxis, HomingState, Position, Toolhead

if TYPE_CHECKING:
    from configfile import ConfigWrapper
    from extras.homing import Homing

axis_mapping: dict[HomingAxis, int] = {
    "x": 0,
    "y": 1,
    "z": 2,
}


def axis_to_index(axis: HomingAxis) -> int:
    return axis_mapping[axis]


@final
class KlipperHomingState(HomingState):
    def __init__(self, homing: Homing):
        self.homing = homing

    @override
    def is_homing(self, axis: HomingAxis) -> bool:
        return axis_to_index(axis) in self.homing.get_axes()

    @override
    def set_homed_position(self, axis: HomingAxis, position: float) -> None:
        coords: list[float | None] = [None, None, None]
        coords[axis_to_index(axis)] = position
        self.homing.set_homed_position(coords)


@final
class KlipperToolhead(Toolhead):
    def __init__(self, config: ConfigWrapper) -> None:
        printer = config.get_printer()
        self.toolhead = printer.lookup_object("toolhead")
        self.motion_report = printer.load_object(config, "motion_report")

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
