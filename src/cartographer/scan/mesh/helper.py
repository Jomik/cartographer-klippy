from __future__ import annotations

import logging
from typing import List, Sequence, Tuple, final

import numpy as np
from configfile import ConfigWrapper
from extras.bed_mesh import BedMeshError
from gcode import GCodeCommand

from cartographer.configuration import CommonConfiguration
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import SampleCountCondition, StreamHandler, TimeCondition
from cartographer.scan.endstop import Model, ScanEndstop
from cartographer.scan.stream import Sample, scan_session

from .nearest_neighbor import cluster_points as nearest_neighbor_cluster_points

logger = logging.getLogger(__name__)


@final
class ScanMeshHelper:
    def __init__(
        self,
        config: ConfigWrapper,
        common_config: CommonConfiguration,
        mcu_helper: McuHelper,
        endstop: ScanEndstop,
        model: Model,
        stream_handler: StreamHandler,
    ):
        self._config = common_config
        self._printer = common_config.get_printer()
        self._endstop = endstop
        self._mcu_helper = mcu_helper
        self._model = model
        self._stream_handler = stream_handler

        self._mesh_config = config.getsection("bed_mesh")
        self._bed_mesh = self._printer.load_object(self._mesh_config, "bed_mesh")
        self._speed = self._mesh_config.getfloat("speed", minval=1.0, default=50.0)

    def calibrate(self, gcmd: GCodeCommand) -> None:
        self._update_bed_mesh_calibrate(gcmd)

        lift_speed = 5.0
        offsets = [self._config.x_offset, self._config.y_offset]

        toolhead = self._printer.lookup_object("toolhead")
        # TODO: Backlash compensation
        toolhead.manual_move([None, None, self._bed_mesh.horizontal_move_z], lift_speed)
        path = self._bed_mesh.bmc.probe_mgr.iter_rapid_path()
        (start, include_start) = next(path)
        toolhead.manual_move(self._apply_offsets(start, offsets), self._speed)
        toolhead.wait_moves()

        samples: List[Tuple[Tuple[float, float], float]] = []
        cluster_points: List[Tuple[float, float]] = []
        if include_start:
            cluster_points.append(self._sample_key(start))

        def collect(sample: Sample) -> bool:
            pos = self._apply_offsets(sample.position[:2], [-i for i in offsets])
            samples.append(
                (
                    (pos[0], pos[1]),
                    sample.distance,
                )
            )
            return False

        with scan_session(
            self._stream_handler, self._mcu_helper, self._model, collect
        ) as session:
            session.wait_for(
                TimeCondition(self._printer, toolhead.get_last_move_time())
            )
            session.wait_for(SampleCountCondition(self._printer, 5))

            for point, include in path:
                pos = self._apply_offsets(point, offsets)
                toolhead.manual_move(pos, self._speed)
                if include:
                    cluster_points.append(self._sample_key(point))

            toolhead.dwell(0.251)
            toolhead.wait_moves()
            session.wait_for(
                TimeCondition(self._printer, toolhead.get_last_move_time())
            )
            session.wait_for(SampleCountCondition(self._printer, 5))

        gcmd.respond_info(f"Collected {len(samples)} samples")

        try:
            positions = self._calculate_positions(samples, cluster_points)
            gcmd.respond_info(f"Calculated {len(positions)} clusters")
        except BedMeshError as e:
            raise gcmd.error(str(e))

        # TODO: Apply user Z offset
        self._bed_mesh.bmc.probe_finalize(offsets + [0], positions)

    def _apply_offsets(self, point: Sequence[float], offsets: list[float]):
        return [(pos - ofs) for pos, ofs in zip(point, offsets)]

    def _sample_key(self, point: Sequence[float]) -> Tuple[float, float]:
        return (round(point[0], 2), round(point[1], 2))

    def _calculate_positions(
        self,
        samples: List[Tuple[Tuple[float, float], float]],
        cluster_points: List[Tuple[float, float]],
    ) -> list[list[float]]:
        clusters = nearest_neighbor_cluster_points(cluster_points, samples)

        positions: list[list[float]] = []
        for key, values in clusters.items():
            if len(values) == 0:
                raise BedMeshError(f"Cluster {key} has no samples")
            positions.append(
                [
                    key[0],
                    key[1],
                    self._endstop.get_position_endstop() - float(np.median(values)),
                ]
            )

        return positions

    def _update_bed_mesh_calibrate(self, gcmd: GCodeCommand) -> None:
        profile_name = gcmd.get("PROFILE", "default")
        if not profile_name.strip():
            raise gcmd.error("Value for parameter 'PROFILE' must be specified")
        self._bed_mesh.set_mesh(None)
        self._bed_mesh.bmc._profile_name = profile_name
        try:
            self._bed_mesh.bmc.update_config(gcmd)
        except BedMeshError as e:
            raise gcmd.error(str(e))
