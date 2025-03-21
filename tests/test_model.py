from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from numpy.polynomial import Polynomial

from cartographer.model import Boundary, Model, Sample
from cartographer.printer_interface import Position, Toolhead

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@dataclass
class MockSample(Sample):
    time: float
    frequency: float


@pytest.fixture
def samples() -> list[Sample]:
    return [MockSample(time=i, frequency=10 + i) for i in range(1, 6)]


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def z_range() -> Boundary:
    return Boundary(0.5, 5.0)


@pytest.fixture
def domain() -> Boundary:
    return Boundary(1.0, 10.0)


@pytest.fixture
def poly(mocker: MockerFixture, domain: Boundary) -> Polynomial:
    def eval_poly(x: float) -> float:
        return x

    poly = mocker.Mock(spec=Polynomial, autospec=True, side_effect=eval_poly)
    poly.domain = domain
    return poly


@pytest.fixture
def model(poly: Polynomial, z_range: Boundary) -> Model:
    return Model(poly, z_range)


@pytest.mark.filterwarnings("ignore:The fit may be poorly conditioned")
def test_fit(toolhead: Toolhead, samples: list[Sample]) -> None:
    def get_requested_position(time: float) -> Position:
        return Position(x=0, y=0, z=time)

    toolhead.get_requested_position = get_requested_position
    model = Model.fit(toolhead, samples)
    assert isinstance(model, Model)
    assert model.z_range.lower < model.z_range.upper


def test_from_coefficients(z_range: Boundary, domain: Boundary) -> None:
    coefficients = [1.0, -2.0, 3.0]
    model = Model.from_coefficients(coefficients, domain, z_range)
    assert isinstance(model, Model)
    assert model.poly.domain[0] == domain.lower  # pyright: ignore[reportAny]
    assert model.poly.domain[1] == domain.upper  # pyright: ignore[reportAny]
    assert model.z_range == z_range


def test_frequency_to_distance(model: Model) -> None:
    frequency = 1 / 3.0
    distance = model.frequency_to_distance(frequency)
    assert isinstance(distance, float)
    assert distance != math.inf and distance != -math.inf


def test_distance_to_frequency(model: Model) -> None:
    distance = 2.5
    frequency = model.distance_to_frequency(distance)
    assert isinstance(frequency, float)
    assert frequency > 0


def test_distance_to_frequency_out_of_range(model: Model) -> None:
    with pytest.raises(RuntimeError, match="Attempted to map out-of-range distance"):
        _ = model.distance_to_frequency(10.0)  # Out of z_range


def test_distance_to_frequency_convergence_error(mocker: MockerFixture, z_range: Boundary, domain: Boundary) -> None:
    def eval_poly(x: float) -> float:
        return x + 100

    poly = mocker.Mock(spec=Polynomial, autospec=True, side_effect=eval_poly)
    poly.domain = domain
    model = Model(poly, z_range)
    with pytest.raises(RuntimeError, match="Model convergence error"):
        _ = model.distance_to_frequency(2.5)
