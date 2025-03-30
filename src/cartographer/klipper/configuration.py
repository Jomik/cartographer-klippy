from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from typing_extensions import override

from cartographer.configuration import (
    CartographerConfiguration,
    ProbeMode,
)
from cartographer.probes.scan_model import Configuration as ScanModelConfiguration
from cartographer.probes.scan_model import Domain

if TYPE_CHECKING:
    from configfile import ConfigWrapper

SCAN_MODEL_PREFIX = "cartographer scan_model"
TOUCH_MODEL_PREFIX = "cartographer touch_model"


T = TypeVar("T", bound=Enum)


def get_enum_choice(config: ConfigWrapper, option: str, enum_type: type[T], default: T) -> T:
    choice = config.get(option, default.value)  #  pyright: ignore[reportAny]
    if choice not in enum_type._value2member_map_:
        msg = f"Invalid choice '{choice}' for option '{option}'"
        raise config.error(msg)
    return enum_type(choice)


class KlipperCartographerConfiguration(CartographerConfiguration):
    x_offset: float
    y_offset: float
    backlash_compensation: float
    probing_mode: ProbeMode
    verbose: bool
    scan_models: dict[str, ScanModelConfiguration]

    def __init__(self, config: ConfigWrapper) -> None:
        self.config: ConfigWrapper = config
        self.x_offset = config.getfloat("x_offset")
        self.y_offset = config.getfloat("y_offset")
        self.backlash_compensation = config.getfloat("backlash_compensation", 0)
        self.probing_mode = get_enum_choice(config, "probing_mode", ProbeMode, ProbeMode.SCAN)
        self.verbose = config.getboolean("verbose", default=False)

        config_name = config.get_name()

        self.scan_models = {
            cfg.name: cfg
            for cfg in map(
                KlipperScanModelConfiguration.from_config, config.get_prefix_sections(f"{config_name} scan_model")
            )
        }


class KlipperScanModelConfiguration(ScanModelConfiguration):
    _config: ConfigWrapper

    @property
    @override
    def name(self) -> str:
        return self._name

    @property
    @override
    def coefficients(self) -> list[float]:
        return self._coefficients

    @property
    @override
    def domain(self) -> Domain:
        return self._domain

    @property
    @override
    def z_offset(self) -> float:
        return self._z_offset

    @override
    def save_z_offset(self, offset: float) -> None:
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(self._config.get_name(), "z_offset", offset)

    @property
    def hash(self) -> str:
        return self._hash

    def __init__(
        self,
        config: ConfigWrapper,
        *,
        name: str,
        coefficients: list[float],
        domain: Domain,
        z_offset: float,
        hash: str,
    ) -> None:
        self._config = config
        self._name: str = name
        self._coefficients: list[float] = coefficients
        self._domain: Domain = domain
        self._z_offset: float = z_offset
        self._hash: str = hash

    @staticmethod
    def from_config(config: ConfigWrapper) -> KlipperScanModelConfiguration:
        name = config.get_name().split("scan_model", 1)[1].strip()
        coefficients = config.getfloatlist("coefficients")
        domain_raw = config.getfloatlist("domain", count=2)
        domain = Domain(domain_raw[0], domain_raw[1])
        z_offset = config.getfloat("z_offset")
        hash = config.get("hash")
        return KlipperScanModelConfiguration(
            config,
            name=name,
            coefficients=coefficients,
            domain=domain,
            z_offset=z_offset,
            hash=hash,
        )


class KlipperProbeConfiguration:
    x_offset: float
    y_offset: float
    z_offset: float

    def __init__(self, config: CartographerConfiguration, probe_config: ScanModelConfiguration) -> None:
        self.x_offset = config.x_offset
        self.y_offset = config.y_offset
        self.z_offset = probe_config.z_offset
