from __future__ import annotations
from typing import final
from configfile import ConfigWrapper
from typing_extensions import override


from cartographer.printer import Position, Toolhead


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
            raise RuntimeError("No dump trapq for toolhead")
        position, _ = trapq.get_trapq_position(time)
        if position is None:
            raise ValueError(f"No position for time {time}")
        return Position(x=position[0], y=position[1], z=position[2])
