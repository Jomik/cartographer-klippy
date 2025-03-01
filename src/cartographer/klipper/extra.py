from __future__ import annotations

from typing import TYPE_CHECKING, final

from cartographer.endstop import Endstop
from cartographer.klipper.endstop import EndstopWrapper
from cartographer.klipper.mcu import KlipperCartographerMcu
from cartographer.modes.none_mode import NoneMode

if TYPE_CHECKING:
    from configfile import ConfigWrapper


def load_config(config: ConfigWrapper):
    return PrinterCartographer(config)


@final
class PrinterCartographer:
    def __init__(self, config: ConfigWrapper) -> None:
        mcu = KlipperCartographerMcu(config)
        endstop = Endstop(mcu, NoneMode())
        _ = EndstopWrapper(mcu, endstop)
