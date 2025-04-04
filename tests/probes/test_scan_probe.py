from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from typing_extensions import TypeAlias, override

from cartographer.printer_interface import HomingState, Mcu, Toolhead
from cartographer.probes.scan_probe import Model, ScanProbe
from cartographer.stream import Session

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@dataclass
class Sample:
    time: float
    frequency: float


Probe: TypeAlias = ScanProbe[object, Sample]


class MockModel(Model):
    @property
    @override
    def z_offset(self) -> float:
        return 0

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
def mcu(mocker: MockerFixture, session: Session[Sample]) -> Mcu[object, Sample]:
    mock = mocker.Mock(spec=Mcu, autospec=True)
    mock.start_session = mocker.Mock(return_value=session)
    return mock


@pytest.fixture
def model() -> Model:
    return MockModel()


@pytest.fixture
def homing_state(mocker: MockerFixture, probe: Probe) -> HomingState:
    mock = mocker.Mock(spec=HomingState, autospec=True)
    mock.endstops = [probe]
    return mock


@pytest.fixture
def probe(mcu: Mcu[object, Sample], toolhead: Toolhead, model: Model) -> Probe:
    return ScanProbe(mcu, toolhead, model=model)


def test_measures_distance(probe: Probe, session: Session[Sample]):
    session.get_items = lambda: [Sample(time=0.0, frequency=i + 1) for i in range(11)]

    distance = probe.measure_distance(skip_count=0)

    assert distance == 6


def test_skips_samples(probe: Probe, session: Session[Sample]):
    session.get_items = lambda: [Sample(time=0.0, frequency=i + 1) for i in range(11)]

    distance = probe.measure_distance(skip_count=4)

    assert distance == 8


def test_raises_error_when_model_is_missing(probe: Probe, model: Model):
    model.distance_to_frequency = lambda distance: 42

    frequency = probe.distance_to_frequency(1.0)

    assert frequency == 42


def test_probe_errors_when_not_homed(probe: Probe, toolhead: Toolhead):
    toolhead.is_homed = lambda axis: False

    with pytest.raises(RuntimeError):
        _ = probe.probe(speed=1.0)


def test_probe_returns_distance(probe: Probe, session: Session[Sample]):
    session.get_items = lambda: [Sample(time=0.0, frequency=42) for _ in range(11)]

    distance = probe.probe(speed=1.0)

    assert distance == 42


def test_probe_errors_outside_range(probe: Probe, session: Session[Sample], model: Model):
    session.get_items = lambda: [Sample(time=0.0, frequency=42) for _ in range(11)]
    model.frequency_to_distance = lambda frequency: float("inf")

    with pytest.raises(RuntimeError):
        _ = probe.probe(speed=1.0)


def test_do_nothing_when_not_homing(mocker: MockerFixture, probe: Probe, homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    homing_state.is_homing_z = lambda: False
    probe.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_do_nothing_when_endstop_not_homing(
    mocker: MockerFixture,
    probe: Probe,
    homing_state: HomingState,
):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    homing_state.is_homing_z = lambda: True
    homing_state.endstops = []
    probe.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_scan_mode_sets_homed_position(
    mocker: MockerFixture,
    probe: Probe,
    homing_state: HomingState,
):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    probe.measure_distance = mocker.Mock(return_value=5)

    _ = probe.home_start(0)
    probe.on_home_end(homing_state)

    homed_position_spy.assert_called_once_with(5)


def test_endstop_is_triggered(mocker: MockerFixture, probe: Probe):
    probe.measure_distance = mocker.Mock(return_value=1)

    assert probe.query_is_triggered(0) is True


def test_endstop_is_not_triggered(mocker: MockerFixture, probe: Probe):
    probe.measure_distance = mocker.Mock(return_value=1)

    assert probe.query_is_triggered(0) is True
