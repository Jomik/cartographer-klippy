from __future__ import annotations

from typing import TYPE_CHECKING, cast

from cartographer.adapters.klipper.adapters import KlipperAdapters

if TYPE_CHECKING:
    from configfile import ConfigWrapper as KlipperConfigWrapper

    from cartographer.interfaces.adapters import Adapters


def init_adapter(config: object) -> Adapters:
    return KlipperAdapters(cast("KlipperConfigWrapper", config))
