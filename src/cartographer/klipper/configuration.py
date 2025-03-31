from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from typing_extensions import override

from cartographer.configuration import CartographerConfiguration
from cartographer.probes.scan_model import Configuration as ScanModelConfiguration
from cartographer.probes.scan_model import Domain
from cartographer.probes.touch_probe import Configuration as TouchModelConfiguration

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
    verbose: bool
    scan_models: dict[str, ScanModelConfiguration]
    touch_models: dict[str, TouchModelConfiguration]

    def __init__(self, config: ConfigWrapper) -> None:
        self.config: ConfigWrapper = config
        self.x_offset = config.getfloat("x_offset")
        self.y_offset = config.getfloat("y_offset")
        self.backlash_compensation = config.getfloat("backlash_compensation", 0)
        self.verbose = config.getboolean("verbose", default=False)

        config_name = config.get_name()

        self.scan_models = {
            cfg.name: cfg
            for cfg in map(
                KlipperScanModelConfiguration.from_config, config.get_prefix_sections(f"{config_name} scan_model")
            )
        }
        self.touch_models = {
            cfg.name: cfg
            for cfg in map(
                KlipperTouchModelConfiguration.from_config, config.get_prefix_sections(f"{config_name} touch_model")
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

    def __init__(
        self,
        config: ConfigWrapper,
        *,
        name: str,
        coefficients: list[float],
        domain: Domain,
        z_offset: float,
    ) -> None:
        self._config = config
        self._name: str = name
        self._coefficients: list[float] = coefficients
        self._domain: Domain = domain
        self._z_offset: float = z_offset

    @staticmethod
    def from_config(config: ConfigWrapper) -> KlipperScanModelConfiguration:
        name = config.get_name().split("scan_model", 1)[1].strip()
        coefficients = config.getfloatlist("coefficients")
        domain_raw = config.getfloatlist("domain", count=2)
        domain = Domain(domain_raw[0], domain_raw[1])
        z_offset = config.getfloat("z_offset")
        return KlipperScanModelConfiguration(
            config,
            name=name,
            coefficients=coefficients,
            domain=domain,
            z_offset=z_offset,
        )


class KlipperTouchModelConfiguration(TouchModelConfiguration):
    _config: ConfigWrapper

    @property
    @override
    def name(self) -> str:
        return self._name

    @property
    @override
    def threshold(self) -> int:
        return self._threshold

    @property
    @override
    def speed(self) -> float:
        return self._speed

    @property
    @override
    def z_offset(self) -> float:
        return self._z_offset

    @override
    def save_z_offset(self, offset: float) -> None:
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(self._config.get_name(), "z_offset", offset)

    @property
    @override
    def samples(self) -> int:
        return self._samples

    @override
    def save_samples(self, samples: int) -> None:
        if samples < 3:
            msg = "number of samples must be at least 3"
            raise ValueError(msg)
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(self._config.get_name(), "samples", samples)
        self._samples = samples

    @property
    @override
    def retries(self) -> int:
        return self._retries

    @override
    def save_retries(self, retries: int) -> None:
        if retries < 0:
            msg = "number of retries must be at least 0"
            raise ValueError(msg)
        configfile = self._config.get_printer().lookup_object("configfile")
        configfile.set(self._config.get_name(), "retries", retries)
        self._retries = retries

    def __init__(
        self,
        config: ConfigWrapper,
        *,
        name: str,
        threshold: int,
        speed: float,
        z_offset: float,
        samples: int,
        retries: int,
    ) -> None:
        self._config = config
        self._name: str = name
        self._threshold: int = threshold
        self._speed: float = speed
        self._z_offset: float = z_offset
        self._samples: int = samples
        self._retries: int = retries

    @staticmethod
    def from_config(config: ConfigWrapper) -> KlipperTouchModelConfiguration:
        name = config.get_name().split("touch_model", 1)[1].strip()
        threshold = config.getint("threshold", minval=1)
        speed = config.getfloat("speed", above=0)
        z_offset = config.getfloat("z_offset", minval=0)
        samples = config.getint("samples", default=5, minval=3)
        retries = config.getint("retries", default=3, minval=0)
        return KlipperTouchModelConfiguration(
            config,
            name=name,
            threshold=threshold,
            speed=speed,
            z_offset=z_offset,
            samples=samples,
            retries=retries,
        )
