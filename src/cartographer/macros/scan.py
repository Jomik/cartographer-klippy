from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Protocol, final

from typing_extensions import override

from cartographer.printer_interface import C, Macro, MacroParams, Position, S, Toolhead
from cartographer.probe.scan_model import ScanModel

if TYPE_CHECKING:
    from cartographer.configuration import ScanModelConfiguration, ScanModelFit
    from cartographer.probe import ScanMode

logger = logging.getLogger(__name__)


class Configuration(Protocol):
    def save_new_scan_model(self, name: str, model: ScanModelFit) -> ScanModelConfiguration: ...


@final
class ScanCalibrateMacro(Macro[MacroParams]):
    name = "SCAN_CALIBRATE"
    description = "Run the scan calibration"

    def __init__(self, probe: ScanMode[C, S], toolhead: Toolhead, config: Configuration) -> None:
        self._probe = probe
        self._toolhead = toolhead
        self._config = config

    @override
    def run(self, params: MacroParams) -> None:
        name = params.get("MODEL_NAME", "default")

        if not self._toolhead.is_homed("x") or not self._toolhead.is_homed("y"):
            msg = "must home x and y before calibration"
            raise RuntimeError(msg)
        _, z_max = self._toolhead.get_z_axis_limits()
        self._toolhead.set_z_position(z=z_max - 10)

        logger.info("Triggering manual probe ")

        self._toolhead.manual_probe(partial(self._handle_manual_probe, name))

    def _handle_manual_probe(self, name: str, pos: Position | None) -> None:
        if pos is None:
            self._toolhead.clear_z_homing_state()
            return

        # TODO: Should this nozzle offset be customizable?
        # We assume the user will move the nozzle to 0.1mm above the bed
        self._toolhead.set_z_position(0.1)

        self._calibrate(name)

    def _calibrate(self, name: str):
        self._toolhead.move(z=5.5, speed=5)
        self._toolhead.wait_moves()

        with self._probe.start_session() as session:
            session.wait_for(lambda samples: len(samples) > 50)
            self._toolhead.dwell(0.250)
            self._toolhead.move(z=0.1, speed=1)
            self._toolhead.dwell(0.250)
            self._toolhead.wait_moves()
            time = self._toolhead.get_last_move_time()
            session.wait_for(lambda samples: samples[-1].time >= time)
            count = len(session.items)
            session.wait_for(lambda samples: len(samples) >= count + 50)
        self._toolhead.move(z=5, speed=5)

        samples = session.get_items()
        logger.debug("Collected %d samples", len(samples))

        model = ScanModel.fit(self._toolhead, samples)
        logger.debug("Scan calibration fitted model: %s", model)

        new_config = self._config.save_new_scan_model(name, model)
        self._probe.model = ScanModel(new_config)
