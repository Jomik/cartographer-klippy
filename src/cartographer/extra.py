from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from cartographer.adapters.klipper import init_adapter
from cartographer.probe.scan_mode import ScanMode, ScanModeConfiguration

if TYPE_CHECKING:
    from cartographer.interfaces.adapters import Adapters

logger = logging.getLogger(__name__)


def load_config(config: object) -> object:
    adapters = init_adapter(config)
    cartographer = PrinterCartographer(adapters)
    return cartographer


@final
class PrinterCartographer:
    def __init__(self, adapters: Adapters) -> None:
        self.scan_mode = ScanMode(
            adapters.mcu,
            adapters.toolhead,
            ScanModeConfiguration.from_config(adapters.config),
        )

        adapters.register_endstop_pin(
            "probe",
            "z_virtual_endstop",
            self.scan_mode,
        )

    # TODO: Move this into an adapter
    def get_status(self, eventtime: float) -> object:
        del eventtime
        return {
            "scan": {},
            "touch": {},
        }
