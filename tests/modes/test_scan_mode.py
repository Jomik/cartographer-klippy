from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from cartographer.modes.scan_mode import Model, Sample, ScanMode, ScanModeMcu
from cartographer.printer import HomingState, Toolhead
from cartographer.stream import Session


@pytest.fixture
def session(mocker: MockerFixture) -> Session[Sample]:
    return Session(mocker.Mock(), mocker.Mock())


@pytest.fixture
def mcu(mocker: MockerFixture, session: Session[Sample]):
    mock = mocker.Mock(spec=ScanModeMcu, autospec=True)
    mock.start_session = mocker.Mock(return_value=session)
    return mock


@pytest.fixture
def toolhead(mocker: MockerFixture):
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def model(mocker: MockerFixture):
    return mocker.Mock(spec=Model, autospec=True)


@pytest.fixture
def mode(toolhead: Toolhead, mcu: ScanModeMcu, model: Model) -> ScanMode:
    return ScanMode(toolhead, mcu, model)


def test_do_nothing_when_not_homing(mocker: MockerFixture, mode: ScanMode):
    homing_state = mocker.Mock(spec=HomingState, autospec=True)
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    homing_state.is_homing = mocker.Mock(return_value=False)
    mode.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_scan_mode_sets_homed_position(
    mocker: MockerFixture, mode: ScanMode, session: Session[Sample]
):
    homing_state = mocker.Mock(spec=HomingState, autospec=True)
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    session.get_items = mocker.Mock(return_value=[Sample(0.0, 5.0, mocker.Mock())] * 15)

    _ = mode.home_start(0)
    mode.on_home_end(homing_state)
    homed_position_spy.assert_called_once_with("z", 5)
