from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.adapters.shared.configuration import KlipperConfiguration
from cartographer.adapters.shared.endstop import KlipperEndstop, KlipperHomingState
from cartographer.adapters.shared.homing import CartographerHomingChip
from cartographer.adapters.shared.mcu.mcu import KlipperCartographerMcu
from cartographer.adapters.shared.printer import KlipperToolhead
from cartographer.adapters.shared.utils import reraise_as_command_error
from cartographer.interfaces.adapters import Adapters

if TYPE_CHECKING:
    from configfile import ConfigWrapper as KlipperConfigWrapper
    from extras.homing import Homing
    from stepper import PrinterRail

    from cartographer.interfaces.printer import Endstop

logger = logging.getLogger(__name__)


@final
class KlipperAdapters(Adapters):
    def __init__(self, config: KlipperConfigWrapper) -> None:
        self._printer = config.get_printer()
        self.config = KlipperConfiguration(config)
        self.mcu = self._mcu = KlipperCartographerMcu(config)
        self.toolhead = KlipperToolhead(config, self.mcu)

        self._printer.register_event_handler("homing:home_rails_end", self._handle_home_rails_end)

    @override
    def register_endstop_pin(self, chip_name: str, pin: str, endstop: Endstop) -> None:
        mcu_endstop = KlipperEndstop(self._mcu, endstop)
        chip = CartographerHomingChip(self._printer, mcu_endstop, pin)
        self._printer.lookup_object("pins").register_chip(chip_name, chip)

    @reraise_as_command_error
    def _handle_home_rails_end(self, homing: Homing, rails: list[PrinterRail]) -> None:
        homing_state = KlipperHomingState(homing)
        klipper_endstops = [
            es.endstop for rail in rails for es, _ in rail.get_endstops() if isinstance(es, KlipperEndstop)
        ]
        for endstop in klipper_endstops:
            endstop.on_home_end(homing_state)
