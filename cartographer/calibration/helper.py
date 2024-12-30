import logging
from dataclasses import dataclass
from typing import Optional, final

from extras import manual_probe
from gcode import GCodeCommand
from toolhead import ToolHead

from cartographer.calibration.model import TRIGGER_DISTANCE, ScanModel
from cartographer.calibration.stream import CalibrationSample, calibration_session
from cartographer.configuration import CommonConfiguration
from cartographer.mcu.helper import McuHelper
from cartographer.mcu.stream import SampleCountCondition, StreamHandler, TimeCondition

logger = logging.getLogger(__name__)


@dataclass
class CalibrationParams:
    model_name: str
    speed: float
    move_speed: float
    x_offset: float
    y_offset: float

    start_height: float = 5.0
    end_height: float = 0.2
    nozzle_offset: float = 0.1


@final
class CalibrationHelper:
    __toolhead: Optional[ToolHead] = None

    @property
    def _toolhead(self) -> ToolHead:
        if self.__toolhead is None:
            self.__toolhead = self._printer.lookup_object("toolhead")
        return self.__toolhead

    def __init__(
        self,
        config: CommonConfiguration,
        mcu_helper: McuHelper,
        stream_handler: StreamHandler,
    ) -> None:
        self._config = config
        self._printer = config.get_printer()
        self._stream_handler = stream_handler
        self._mcu_helper = mcu_helper

    def get_calibration_params(self, gcmd: GCodeCommand) -> CalibrationParams:
        return CalibrationParams(
            model_name=gcmd.get("MODEL_NAME", "default"),
            speed=gcmd.get_float("SPEED", minval=1.0, maxval=5.0, default=1.0),
            move_speed=gcmd.get_float(
                "MOVE_SPEED", minval=1.0, maxval=50.0, default=self._config.move_speed
            ),
            x_offset=self._config.x_offset,
            y_offset=self._config.y_offset,
        )

    def start_calibration(self, gcmd: GCodeCommand) -> None:
        manual_probe.verify_no_manual_probe(self._printer)
        params = self.get_calibration_params(gcmd)

        curtime = self._printer.get_reactor().monotonic()
        kin_status = self._toolhead.get_status(curtime)
        if "xy" not in kin_status["homed_axes"]:
            raise self._printer.command_error("Must home X and Y before calibration")

        forced_z = self._force_z_position(params)
        _ = manual_probe.ManualProbeHelper(
            self._printer,
            gcmd,
            lambda kin_pos: self._finalize_manual_probe(params, forced_z, kin_pos),
        )

    def _finalize_manual_probe(
        self,
        params: CalibrationParams,
        forced_z: bool,
        kin_pos: Optional["list[float]"],
    ) -> None:
        if kin_pos is not None:
            self._calibrate(params)
        elif forced_z:
            self._toolhead.get_kinematics().note_z_not_homed()

    def _calibrate(self, params: CalibrationParams) -> None:
        self._reset_coordinate_system(params)
        origpos = self._toolhead.get_position()[:]

        self._move_probe_to_nozzle_position(params)
        samples = self._run_calibration_moves(params)

        self._move_to_start_position(origpos, params)

        model = ScanModel.fit(self._printer, params.model_name, samples)
        model.save()

    def _run_calibration_moves(
        self, params: CalibrationParams
    ) -> "list[CalibrationSample]":
        samples: list[CalibrationSample] = []

        def receive_sample(sample: CalibrationSample) -> bool:
            samples.append(sample)
            return False

        self._toolhead.flush_step_generation()
        with calibration_session(
            self._stream_handler,
            self._mcu_helper,
            receive_sample,
        ) as session:
            session.wait_for(
                TimeCondition(self._printer, self._toolhead.get_last_move_time()),
            )
            session.wait_for(
                SampleCountCondition(self._printer, 50),
            )
            self._toolhead.dwell(0.250)
            self._toolhead.manual_move([None, None, params.end_height], params.speed)
            self._toolhead.flush_step_generation()
            session.wait_for(
                TimeCondition(self._printer, self._toolhead.get_last_move_time())
            )
            session.wait_for(SampleCountCondition(self._printer, 50))

        return samples

    def _force_z_position(self, params: CalibrationParams) -> bool:
        curtime = self._printer.get_reactor().monotonic()
        kin_status = self._toolhead.get_status(curtime)

        if "z" in kin_status["homed_axes"]:
            return False

        _ = self._toolhead.get_last_move_time()
        pos = self._toolhead.get_position()
        pos[2] = kin_status["axis_maximum"][2] - TRIGGER_DISTANCE - params.start_height
        self._toolhead.set_position(pos, homing_axes=[2])
        return True

    def _reset_coordinate_system(self, params: CalibrationParams):
        self._toolhead.wait_moves()
        _ = self._toolhead.get_last_move_time()

        curpos = self._toolhead.get_position()
        curpos[2] = params.nozzle_offset
        self._toolhead.set_position(curpos)

    def _move_probe_to_nozzle_position(self, params: CalibrationParams) -> None:
        # TODO: Consider backlash
        self._toolhead.manual_move([None, None, params.start_height], params.move_speed)

        curpos = self._toolhead.get_position()
        probepos = [curpos[0] - params.x_offset, curpos[1] - params.y_offset]
        self._toolhead.manual_move(probepos, params.move_speed)

        self._toolhead.wait_moves()

    def _move_to_start_position(
        self, origpos: "list[float]", params: CalibrationParams
    ):
        self._toolhead.manual_move([None, None, params.start_height], params.move_speed)
        self._toolhead.manual_move(origpos[:2], params.move_speed)
