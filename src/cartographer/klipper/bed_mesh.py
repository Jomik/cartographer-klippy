from __future__ import annotations

from typing import TYPE_CHECKING, final

from extras.bed_mesh import BedMeshError
from gcode import GCodeCommand, GCodeDispatch
from typing_extensions import override

from cartographer.macros.bed_mesh import Configuration, MeshHelper, MeshPoint
from cartographer.printer_interface import Position

if TYPE_CHECKING:
    from configfile import ConfigWrapper

    from cartographer.configuration import (
        Configuration as CartographerConfiguration,
    )


class KlipperMeshConfiguration(Configuration):
    def __init__(self, *, speed: float, scan_height: float, runs: int, zero_reference_position: Position) -> None:
        self.speed: float = speed
        self.scan_height: float = scan_height
        self.runs: int = runs
        self.zero_reference_position: Position = zero_reference_position

    @staticmethod
    def from_config(config: ConfigWrapper, cartographer_config: CartographerConfiguration) -> KlipperMeshConfiguration:
        mesh_config = config.getsection("bed_mesh")
        speed = mesh_config.getfloat("speed", default=50, above=0)
        scan_height = mesh_config.getfloat("horizontal_move_z", default=4, above=0)
        (zrp_x, zrp_y) = mesh_config.getfloatlist("zero_reference_position", count=2)
        zero_reference_position = Position(
            zrp_x,
            zrp_y,
            10,
        )
        return KlipperMeshConfiguration(
            speed=speed,
            scan_height=scan_height,
            runs=cartographer_config.scan_mesh_runs,
            zero_reference_position=zero_reference_position,
        )


@final
class KlipperMeshHelper(MeshHelper[GCodeCommand]):
    def __init__(self, config: ConfigWrapper, gcode: GCodeDispatch) -> None:
        mesh_config = config.getsection("bed_mesh")
        self._bed_mesh = config.get_printer().load_object(mesh_config, "bed_mesh")
        # Loading "bed_mesh" above registers the command.
        self.macro = gcode.register_command("BED_MESH_CALIBRATE", None)

    @override
    def orig_macro(self, params: GCodeCommand) -> None:
        if self.macro is not None:
            self.macro(params)

    @override
    def prepare(self, params: GCodeCommand) -> None:
        profile_name = params.get("PROFILE", "default")
        if not profile_name.strip():
            msg = "value for parameter 'PROFILE' must be specified"
            raise RuntimeError(msg)
        self._bed_mesh.set_mesh(None)
        self._bed_mesh.bmc._profile_name = profile_name
        try:
            self._bed_mesh.bmc.update_config(params)
        except BedMeshError as e:
            raise RuntimeError(str(e)) from e

    @override
    def generate_path(self) -> list[MeshPoint]:
        path = self._bed_mesh.bmc.probe_mgr.iter_rapid_path()
        return [MeshPoint(p[0], p[1], include) for (p, include) in path]

    @override
    def finalize(self, offset: Position, positions: list[Position]):
        self._bed_mesh.bmc.probe_finalize(
            [offset.x, offset.y, offset.z],
            [[p.x, p.y, p.z] for p in positions],
        )
