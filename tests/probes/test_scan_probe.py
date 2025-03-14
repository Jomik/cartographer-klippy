from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from typing_extensions import override

from cartographer.printer import Toolhead
from cartographer.probes.scan_probe import Mcu, Model, ScanProbe
from cartographer.stream import Session

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@dataclass
class Sample:
    time: float
    frequency: float


class MockModel(Model):
    @override
    def distance_to_frequency(self, distance: float) -> float:
        return distance

    @override
    def frequency_to_distance(self, frequency: float) -> float:
        return frequency


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def session(mocker: MockerFixture) -> Session[Sample]:
    return Session(mocker.Mock(), mocker.Mock())


@pytest.fixture
def mcu(mocker: MockerFixture, session: Session[Sample]) -> Mcu[Sample]:
    mock = mocker.Mock(spec=Mcu, autospec=True)
    mock.start_session = mocker.Mock(return_value=session)
    return mock


@pytest.fixture
def model() -> Model:
    return MockModel()


@pytest.fixture
def probe(mcu: Mcu[Sample], toolhead: Toolhead, model: Model) -> ScanProbe[Sample]:
    return ScanProbe(mcu, toolhead, model=model)


def test_measures_distance(probe: ScanProbe[Sample], session: Session[Sample]):
    session.get_items = lambda: [Sample(time=0.0, frequency=i + 1) for i in range(11)]

    distance = probe.measure_distance(skip_count=0)

    assert distance == 6


def test_skips_samples(probe: ScanProbe[Sample], session: Session[Sample]):
    session.get_items = lambda: [Sample(time=0.0, frequency=i + 1) for i in range(11)]

    distance = probe.measure_distance(skip_count=4)

    assert distance == 8


def test_raises_error_when_model_is_missing(probe: ScanProbe[Sample]):
    probe.model = None

    with pytest.raises(RuntimeError):
        _ = probe.distance_to_frequency(0.0)

    with pytest.raises(RuntimeError):
        _ = probe.measure_distance()


def test_converts_distance_to_frequency(probe: ScanProbe[Sample], model: Model):
    model.distance_to_frequency = lambda distance: 42

    frequency = probe.distance_to_frequency(1.0)

    assert frequency == 42
