from __future__ import annotations

from typing import TYPE_CHECKING, Callable, NamedTuple, Protocol

from numpy.polynomial import Polynomial

if TYPE_CHECKING:
    from cartographer.printer_interface import Toolhead


class Sample(Protocol):
    time: float
    frequency: float


MAX_TOLERANCE = 1e-8
ITERATIONS = 50
DEGREES = 9

polynomial_fit: Callable[[list[float], list[float], int], Polynomial] = Polynomial.fit  # pyright:ignore[reportUnknownMemberType]


class Boundary(NamedTuple):
    lower: float
    upper: float


# TODO: Temperature compensation
class Model:
    poly: Polynomial
    z_range: Boundary

    def __init__(self, poly: Polynomial, z_range: Boundary) -> None:
        self.poly = poly
        self.z_range = z_range

    @staticmethod
    def fit(toolhead: Toolhead, samples: list[Sample]) -> Model:
        z_offsets = [toolhead.get_requested_position(sample.time).z for sample in samples]
        inverse_frequencies = [1 / sample.frequency for sample in samples]

        poly = polynomial_fit(inverse_frequencies, z_offsets, DEGREES)

        return Model(poly, Boundary(min(z_offsets), max(z_offsets)))

    @staticmethod
    def from_coefficients(coefficients: list[float], domain: Boundary, z_range: Boundary) -> Model:
        poly = Polynomial(coefficients, domain)
        return Model(poly, z_range)

    def frequency_to_distance(self, frequency: float) -> float:
        lower_bound, upper_bound = self._domain()
        inverse_frequency = 1 / frequency

        if inverse_frequency > upper_bound:
            return float("inf")
        elif inverse_frequency < lower_bound:
            return float("-inf")

        return self._eval(inverse_frequency)

    def distance_to_frequency(self, distance: float) -> float:
        min_z, max_z = self.z_range
        if distance < min_z or distance > max_z:
            msg = f"Attempted to map out-of-range distance {distance:.3f}, valid range [{min_z:.3f}, {max_z:.3f}]"
            raise RuntimeError(msg)

        lower_bound, upper_bound = self._domain()

        for _ in range(ITERATIONS):
            midpoint = (upper_bound + lower_bound) / 2
            value = self._eval(midpoint)

            if abs(value - distance) < MAX_TOLERANCE:
                return float(1.0 / midpoint)
            elif value < distance:
                lower_bound = midpoint
            else:
                upper_bound = midpoint

        msg = "Model convergence error"
        raise RuntimeError(msg)

    def _eval(self, x: float) -> float:
        return float(self.poly(x))  # pyright: ignore[reportUnknownArgumentType]

    def _domain(self) -> Boundary:
        lower_bound, upper_bound = self.poly.domain  # pyright: ignore[reportAny]
        return Boundary(lower_bound, upper_bound)
