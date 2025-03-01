from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from cartographer.endstop import Endstop, Mcu
from cartographer.modes.base_mode import EndstopMode


@pytest.fixture
def mcu(mocker: MockerFixture):
    return mocker.Mock(spec=Mcu, autospec=True)


@pytest.fixture
def start_mode(mocker: MockerFixture) -> EndstopMode:
    return mocker.Mock(spec=EndstopMode, autospec=True)


@pytest.fixture
def end_mode(mocker: MockerFixture) -> EndstopMode:
    return mocker.Mock(spec=EndstopMode, autospec=True)


@pytest.fixture
def endstop(mcu: Mcu, start_mode: EndstopMode):
    return Endstop(mcu, start_mode)


def test_endstop_switches_mode(
    endstop: Endstop, start_mode: EndstopMode, end_mode: EndstopMode
):
    assert endstop.current_mode() == start_mode
    endstop.set_mode(end_mode)
    assert endstop.current_mode() == end_mode


def test_endstop_calls_on_enter(
    mocker: MockerFixture, mcu: Mcu, start_mode: EndstopMode
):
    spy_enter = mocker.spy(start_mode, "on_enter")
    _ = Endstop(mcu, start_mode)
    assert spy_enter.call_count == 1


def test_endstop_calls_on_exit(
    mocker: MockerFixture,
    endstop: Endstop,
    start_mode: EndstopMode,
    end_mode: EndstopMode,
):
    spy_exit = mocker.spy(start_mode, "on_exit")
    endstop.set_mode(end_mode)
    assert spy_exit.call_count == 1
