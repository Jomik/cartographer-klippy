from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cartographer.endstops.scan_endstop import Mcu, Probe, ScanEndstop
from cartographer.printer import HomingState, Toolhead

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def mcu(mocker: MockerFixture) -> Mcu:
    return mocker.Mock(spec=Mcu, autospec=True)


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def probe(mocker: MockerFixture) -> Probe:
    return mocker.Mock(spec=Probe, autospec=True)


@pytest.fixture
def endstop(toolhead: Toolhead, mcu: Mcu, probe: Probe) -> ScanEndstop:
    return ScanEndstop(toolhead, mcu, probe)


@pytest.fixture
def homing_state(mocker: MockerFixture, endstop: ScanEndstop) -> HomingState:
    mock = mocker.Mock(spec=HomingState, autospec=True)
    mock.endstops = [endstop]
    return mock


def test_do_nothing_when_not_homing(mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    homing_state.is_homing = lambda axis: False
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_do_nothing_when_endstop_not_homing(mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    homing_state.is_homing = lambda axis: axis == "z"
    homing_state.endstops = []
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_scan_mode_sets_homed_position(
    mocker: MockerFixture, endstop: ScanEndstop, homing_state: HomingState, probe: Probe
):
    homed_position_spy = mocker.spy(homing_state, "set_homed_position")
    probe.measure_distance = mocker.Mock(return_value=5)

    _ = endstop.home_start(0)
    endstop.on_home_end(homing_state)

    homed_position_spy.assert_called_once_with("z", 5)
