from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Protocol, cast

from numpy.polynomial import Polynomial

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cartographer.configuration import ScanModelConfiguration
    from cartographer.printer_interface import Toolhead


class Sample(Protocol):
    time: float
    frequency: float


MAX_TOLERANCE = 1e-8
ITERATIONS = 50
DEGREES = 9


class Domain(NamedTuple):
    lower: float
    upper: float


# TODO: Temperature compensation
class ScanModel:
    config: ScanModelConfiguration
    _poly: Polynomial | None = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def z_offset(self) -> float:
        return self.config.z_offset

    def save_z_offset(self, new_offset: float) -> None:
        self.config.save_z_offset(new_offset)

    @property
    def poly(self) -> Polynomial:
        if self._poly is None:
            self._poly = Polynomial(self.config.coefficients, self.config.domain)
        return self._poly

    def __init__(self, config: ScanModelConfiguration) -> None:
        self.config = config

    @staticmethod
    def fit(toolhead: Toolhead, samples: Sequence[Sample]) -> Polynomial:
        z_offsets = [toolhead.get_requested_position(sample.time).z for sample in samples]
        inverse_frequencies = [1 / sample.frequency for sample in samples]

        poly = cast("Polynomial", Polynomial.fit(inverse_frequencies, z_offsets, DEGREES))
        return poly

    def frequency_to_distance(self, frequency: float) -> float:
        lower_bound, upper_bound = self.config.domain
        inverse_frequency = 1 / frequency

        if inverse_frequency > upper_bound:
            return float("inf")
        elif inverse_frequency < lower_bound:
            return float("-inf")

        return self._eval(inverse_frequency) - self.config.z_offset

    def distance_to_frequency(self, distance: float) -> float:
        # PERF: We can use brentq if scipy is available
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html#scipy.optimize.brentq
        distance += self.config.z_offset
        min_z, max_z = self._get_z_range()
        if distance < min_z or distance > max_z:
            msg = f"attempted to map out-of-range distance {distance:.3f}, valid range [{min_z:.3f}, {max_z:.3f}]"
            raise RuntimeError(msg)

        lower_bound, upper_bound = self.config.domain

        for _ in range(ITERATIONS):
            midpoint = (upper_bound + lower_bound) / 2
            value = self._eval(midpoint)

            if abs(value - distance) < MAX_TOLERANCE:
                return float(1.0 / midpoint)
            elif value < distance:
                lower_bound = midpoint
            else:
                upper_bound = midpoint

        msg = "model convergence error"
        raise RuntimeError(msg)

    _z_range: Domain | None = None

    def _get_z_range(self) -> Domain:
        if self._z_range is None:
            min, max = self.config.domain
            self._z_range = Domain(self._eval(min), self._eval(max))
        return self._z_range

    def _eval(self, x: float) -> float:
        return float(self.poly(x))  # pyright: ignore[reportUnknownArgumentType]
