from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typing_extensions import override

from cartographer.endstops.scan_endstop import Mcu, Model, Sample, ScanEndstop
from cartographer.printer import HomingState, Toolhead
from cartographer.stream import Session

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def session(mocker: MockerFixture) -> Session[Sample]:
    return Session(mocker.Mock(), mocker.Mock())


@pytest.fixture
def mcu(mocker: MockerFixture, session: Session[Sample]):
    mock = mocker.Mock(spec=Mcu, autospec=True)
    mock.start_session = mocker.Mock(return_value=session)
    return mock


@pytest.fixture
def toolhead(mocker: MockerFixture):
    return mocker.Mock(spec=Toolhead, autospec=True)


class MockModel(Model):
    @override
    def distance_to_frequency(self, distance: float) -> float:
        return distance

    @override
    def frequency_to_distance(self, frequency: float) -> float:
        return frequency


@pytest.fixture
def model():
    return MockModel()


@pytest.fixture
def endstop(toolhead: Toolhead, mcu: Mcu, model: Model) -> ScanEndstop:
    return ScanEndstop(toolhead, mcu, model)


@pytest.fixture
def homing_state(mocker: MockerFixture, endstop: ScanEndstop) -> HomingState:
    mock = mocker.Mock(spec=HomingState, autospec=True)
    mock.endstops = [endstop]
    return mock


def test_do_nothing_when_not_homing(mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    homing_state.is_homing = mocker.Mock(return_value=False)
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_do_nothing_when_endstop_not_homing(mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    homing_state.is_homing = mocker.Mock(return_value=True)
    homing_state.endstops = []
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_scan_mode_sets_homed_position(
    mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState, session: Session[Sample]
):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    session.get_items = mocker.Mock(return_value=[Sample(time=0.0, frequency=5, temperature=10)] * 15)

    _ = endstop.home_start(0)
    endstop.on_home_end(homing_state)
    homed_position_spy.assert_called_once_with("z", 5)
