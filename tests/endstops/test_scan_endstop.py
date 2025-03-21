from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cartographer.endstops.scan_endstop import Mcu, Probe, ScanEndstop
from cartographer.printer import HomingState

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def mcu(mocker: MockerFixture) -> Mcu[object]:
    return mocker.Mock(spec=Mcu, autospec=True)


@pytest.fixture
def probe(mocker: MockerFixture) -> Probe:
    return mocker.Mock(spec=Probe, autospec=True)


@pytest.fixture
def endstop(mcu: Mcu[object], probe: Probe) -> ScanEndstop[object]:
    return ScanEndstop(mcu, probe)


@pytest.fixture
def homing_state(mocker: MockerFixture, endstop: ScanEndstop[object]) -> HomingState:
    mock = mocker.Mock(spec=HomingState, autospec=True)
    mock.endstops = [endstop]
    return mock


def test_do_nothing_when_not_homing(mocker: MockerFixture, endstop: ScanEndstop[object], homing_state: HomingState):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    homing_state.is_homing_z = lambda: False
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_do_nothing_when_endstop_not_homing(
    mocker: MockerFixture,
    endstop: ScanEndstop[object],
    homing_state: HomingState,
):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    homing_state.is_homing_z = lambda: True
    homing_state.endstops = []
    endstop.on_home_end(homing_state)
    assert homed_position_spy.call_count == 0


def test_scan_mode_sets_homed_position(
    mocker: MockerFixture,
    endstop: ScanEndstop[object],
    homing_state: HomingState,
    probe: Probe,
):
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")
    probe.measure_distance = mocker.Mock(return_value=5)

    _ = endstop.home_start(0)
    endstop.on_home_end(homing_state)

    homed_position_spy.assert_called_once_with(5)


def test_endstop_is_triggered(endstop: ScanEndstop[object], probe: Probe):
    probe.measure_distance = lambda time=0: 1

    assert endstop.query_is_triggered(0) is True


def test_endstop_is_not_triggered(endstop: ScanEndstop[object], probe: Probe):
    probe.measure_distance = lambda time=0: 1

    assert endstop.query_is_triggered(0) is True
