# https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/none.py
from typing import TypedDict

import gcode
from ..stepper import MCU_stepper
# NOTE: We use NoneKinematics as it is a dummy implementation.
# It implements the minimum kinematics interface.

type _Pos = list[float]

class _Status(TypedDict):
    homed_axes: str
    axis_minimum: gcode.Coord
    axis_maximum: gcode.Coord

class NoneKinematics:
    def get_steppers(self) -> list[MCU_stepper]: ...
    def get_status(self, eventtime: float) -> _Status: ...
    def calc_position(self, stepper_positions: dict[str, _Pos]) -> _Pos: ...
    def note_z_not_homed(self) -> None: ...
