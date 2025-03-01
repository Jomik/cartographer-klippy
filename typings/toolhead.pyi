# https://github.com/Klipper3d/klipper/blob/master/klippy/toolhead.py
from collections.abc import Sequence
from typing import TypedDict

import gcode

from kinematics import Kinematics
from kinematics import Status as KinematicsStatus
from kinematics.extruder import Extruder

class _Status(KinematicsStatus, TypedDict):
    print_time: float
    stalls: int
    estimated_print_time: float
    extruder: str
    position: gcode.Coord
    max_velocity: float
    max_accel: float
    minimum_cruise_ratio: float
    square_corner_velocity: float

type _Pos = list[float]

class ToolHead:
    Coord: type[gcode.Coord]
    def get_kinematics(self) -> Kinematics: ...
    def get_extruder(self) -> Extruder: ...
    def get_status(self, eventtime: float) -> _Status: ...
    def get_position(self) -> _Pos: ...
    def set_position(self, newpos: _Pos, homing_axes: Sequence[int] = ()) -> None: ...
    def move(self, newpos: _Pos, speed: float) -> None: ...
    def wait_moves(self) -> None: ...
    def dwell(self, delay: float) -> None: ...
    def flush_step_generation(self) -> None: ...
    def manual_move(self, coord: _Pos | list[float | None], speed: float) -> None: ...
    def get_trapq(self) -> str: ...
    def get_last_move_time(self) -> float: ...
