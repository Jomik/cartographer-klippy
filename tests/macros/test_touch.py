from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from typing_extensions import TypeAlias

from cartographer.macros.touch import TouchAccuracyMacro, TouchHomeMacro, TouchMacro
from cartographer.printer_interface import MacroParams, Position, Toolhead
from cartographer.probes.touch_probe import TouchProbe

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

Probe: TypeAlias = TouchProbe[object]


@pytest.fixture
def offset() -> Position:
    return Position(0, 0, 0)


@pytest.fixture
def probe(mocker: MockerFixture, offset: Position) -> Probe:
    mock = mocker.Mock(spec=Probe, autospec=True)
    mock.offset = offset
    return mock


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def params(mocker: MockerFixture) -> MacroParams:
    return mocker.Mock(
        spec=MacroParams,
        autospec=True,
    )


def test_touch_macro_output(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: Probe,
    params: MacroParams,
):
    macro = TouchMacro(probe)
    probe.probe = mocker.Mock(return_value=5.0)

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "Result is z=5.000000" in caplog.messages


def test_touch_accuracy_macro_output(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: Probe,
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = TouchAccuracyMacro(probe, toolhead)
    params.get_int = mocker.Mock(return_value=10)
    toolhead.get_position = lambda: Position(0, 0, 0)
    params.get_float = mocker.Mock(return_value=1)
    i = -1
    measurements: list[float] = [50 + i * 10 for i in range(10)]

    def mock_probe(**_) -> float:
        nonlocal i
        i += 1
        return measurements[i]

    probe.probe = mock_probe

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "touch accuracy results" in caplog.text
    assert "minimum 50" in caplog.text
    assert "maximum 140" in caplog.text
    assert "range 90" in caplog.text
    assert "average 95" in caplog.text
    assert "median 95" in caplog.text
    assert "standard deviation 28" in caplog.text


def test_touch_accuracy_macro_sample_count(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: Probe,
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = TouchAccuracyMacro(probe, toolhead)
    params.get_int = mocker.Mock(return_value=3)
    toolhead.get_position = lambda: Position(0, 0, 0)
    params.get_float = mocker.Mock(return_value=1)
    i = -1
    measurements: list[float] = [50 + i * 10 for i in range(10)]

    def mock_probe(**_) -> float:
        nonlocal i
        i += 1
        return measurements[i]

    probe.probe = mock_probe

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "touch accuracy results" in caplog.text
    assert "minimum 50" in caplog.text
    assert "maximum 70" in caplog.text
    assert "range 20" in caplog.text
    assert "average 60" in caplog.text
    assert "median 60" in caplog.text
    assert "standard deviation 8" in caplog.text


def test_touch_home_macro(
    mocker: MockerFixture,
    probe: Probe,
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = TouchHomeMacro(probe, toolhead)
    probe.probe = mocker.Mock(return_value=0.1)
    toolhead.get_position = mocker.Mock(return_value=Position(0, 0, 2))
    set_z_position_spy = mocker.spy(toolhead, "set_z_position")

    macro.run(params)

    assert set_z_position_spy.mock_calls == [mocker.call(1.9)]


def test_touch_home_macro_with_z_offset(
    mocker: MockerFixture,
    probe: Probe,
    offset: Position,
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = TouchHomeMacro(probe, toolhead)
    probe.probe = mocker.Mock(return_value=0.0)
    offset.z = 0.1
    toolhead.get_position = mocker.Mock(return_value=Position(0, 0, 2))
    set_z_position_spy = mocker.spy(toolhead, "set_z_position")

    macro.run(params)

    assert set_z_position_spy.mock_calls == [mocker.call(1.9)]
