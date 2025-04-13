from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from numpy.polynomial import Polynomial

from cartographer.printer_interface import Position, Toolhead
from cartographer.probes.scan_model import Sample, ScanModel

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from cartographer.configuration import ScanModelConfiguration


@dataclass
class MockSample(Sample):
    time: float
    frequency: float


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    mock = mocker.Mock(spec=Toolhead, autospec=True)

    def get_requested_position(time: float) -> Position:
        return Position(x=0, y=0, z=time)

    mock.get_requested_position = get_requested_position

    return mock


class MockConfiguration:
    name: str = "default"
    coefficients: list[float] = [1 / 3.0] * 9
    domain: tuple[float, float] = (1, 3)
    z_offset: float = 0

    def save_z_offset(self, new_offset: float) -> None:
        self.z_offset = new_offset


@pytest.fixture
def config() -> ScanModelConfiguration:
    return MockConfiguration()


@pytest.fixture
def model(mocker: MockerFixture, config: MockConfiguration) -> ScanModel:
    def eval_poly(x: float) -> float:
        return x

    poly = mocker.Mock(spec=Polynomial, autospec=True, side_effect=eval_poly)
    poly.domain = config.domain

    model = ScanModel(config)
    # model._poly = poly
    return model


@pytest.mark.filterwarnings("ignore:The fit may be poorly conditioned")
def test_fit(toolhead: Toolhead) -> None:
    samples = [MockSample(time=i, frequency=1 / i) for i in range(1, 20)]

    poly = ScanModel.fit(toolhead, samples)

    assert poly(10) == pytest.approx(10.0)  # pyright: ignore[reportUnknownMemberType]


def test_from_config(config: ScanModelConfiguration) -> None:
    model = ScanModel(config)
    assert isinstance(model, ScanModel)
    assert model.poly.domain[0] == config.domain[0]  # pyright: ignore[reportAny]
    assert model.poly.domain[1] == config.domain[1]  # pyright: ignore[reportAny]


def test_frequency_to_distance(model: ScanModel) -> None:
    frequency = 1 / 3.0
    distance = model.frequency_to_distance(frequency)
    assert isinstance(distance, float)
    assert distance != math.inf and distance != -math.inf


def test_distance_to_frequency(model: ScanModel) -> None:
    distance = 2.5
    frequency = model.distance_to_frequency(distance)
    assert isinstance(frequency, float)
    assert frequency > 0


def test_distance_to_frequency_out_of_range(model: ScanModel) -> None:
    with pytest.raises(RuntimeError, match="attempted to map out-of-range distance"):
        _ = model.distance_to_frequency(11)  # Out of z_range


def test_frequency_to_distance_applies_offset(model: ScanModel, config: ScanModelConfiguration) -> None:
    config.z_offset = 0.5
    frequency = 1 / 3.0

    distance = model.frequency_to_distance(frequency)

    assert distance == 2.5


def test_distance_to_frequency_applies_offset(model: ScanModel, config: ScanModelConfiguration) -> None:
    config.z_offset = 0.5
    distance = 2.5

    frequency = model.distance_to_frequency(distance)

    assert frequency == pytest.approx(1 / 3)  # pyright: ignore[reportUnknownMemberType]


def test_frequency_to_distance_out_of_range(model: ScanModel) -> None:
    high_frequency_dist = model.frequency_to_distance(1000000)  # Out of z_range
    low_frequency_dist = model.frequency_to_distance(0.1)  # Out of z_range

    assert low_frequency_dist == float("inf")
    assert high_frequency_dist == float("-inf")
