# https://github.com/Klipper3d/klipper/blob/master/klippy/extras/bed_mesh.py
from collections.abc import Iterator
from typing import Literal, TypedDict

from gcode import GCodeCommand

class BedMeshError(Exception): ...

class _Params(TypedDict):
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    x_count: int
    y_count: int
    mesh_x_pps: int
    mesh_y_pps: int
    algo: Literal["lagrange", "bicubic", "direct"]
    tension: float

class ZMesh:
    def __init__(self, params: _Params, name: str | None) -> None: ...
    def build_mesh(self, z_matrix: list[list[float]]) -> None: ...

class BedMesh:
    bmc: BedMeshCalibrate
    horizontal_move_z: float
    def set_mesh(self, mesh: ZMesh | None) -> None: ...
    def save_profile(self, profile_name: str) -> None: ...

class BedMeshCalibrate:
    mesh_config: _Params
    probe_mgr: ProbeManager
    _profile_name: str
    def update_config(self, gcmd: GCodeCommand) -> None: ...
    def probe_finalize(self, offsets: list[float], positions: list[list[float]]) -> None: ...

class ProbeManager:
    def iter_rapid_path(self) -> Iterator[tuple[tuple[float, float], bool]]: ...
    def get_std_path(self) -> list[tuple[float, float]]: ...
