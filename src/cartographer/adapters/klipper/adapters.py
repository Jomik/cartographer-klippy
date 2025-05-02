from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.adapters.shared.configuration import KlipperConfiguration
from cartographer.adapters.shared.endstop import KlipperEndstop
from cartographer.adapters.shared.homing import CartographerHomingChip
from cartographer.adapters.shared.mcu.mcu import KlipperCartographerMcu
from cartographer.adapters.shared.printer import KlipperToolhead
from cartographer.interfaces.adapters import Adapters

if TYPE_CHECKING:
    from configfile import ConfigWrapper as KlipperConfigWrapper

    from cartographer.interfaces.printer import Endstop

logger = logging.getLogger(__name__)


@final
class KlipperAdapters(Adapters):
    def __init__(self, config: KlipperConfigWrapper) -> None:
        self._printer = config.get_printer()
        self.config = KlipperConfiguration(config)
        self.mcu = self._mcu = KlipperCartographerMcu(config)
        self.toolhead = KlipperToolhead(config, self.mcu)

    @override
    def register_endstop_pin(self, chip_name: str, pin: str, endstop: Endstop) -> None:
        mcu_endstop = KlipperEndstop(self._mcu, endstop)
        chip = CartographerHomingChip(self._printer, mcu_endstop, pin)
        self._printer.lookup_object("pins").register_chip(chip_name, chip)
