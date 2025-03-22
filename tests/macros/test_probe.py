from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from cartographer.endstops.scan_endstop import ScanEndstop
from cartographer.macros.probe import ProbeAccuracyMacro, ProbeMacro, QueryProbe, ZOffsetApplyProbe
from cartographer.printer_interface import MacroParams, Position, Sample, Toolhead
from cartographer.probes.scan_probe import ScanProbe

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


@pytest.fixture
def probe(mocker: MockerFixture) -> ScanProbe[Sample]:
    return mocker.Mock(spec=ScanProbe, autospec=True)


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.Mock(spec=Toolhead, autospec=True)


@pytest.fixture
def endstop(mocker: MockerFixture) -> ScanEndstop[object, Sample]:
    return mocker.Mock(spec=ScanEndstop, autospec=True)


@pytest.fixture
def params(mocker: MockerFixture):
    return mocker.Mock(
        spec=MacroParams,
        autospec=True,
    )


def test_probe_macro_output(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: ScanProbe[Sample],
    params: MacroParams,
):
    macro = ProbeMacro(probe)
    probe.probe = mocker.Mock(return_value=5.0)

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "Result is z=5.000000" in caplog.messages


def test_probe_accuracy_macro_output(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: ScanProbe[Sample],
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = ProbeAccuracyMacro(probe, toolhead)
    probe.probe_height = 2
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

    assert "probe accuracy results" in caplog.text
    assert "minimum 50.000000" in caplog.text
    assert "maximum 140.000000" in caplog.text
    assert "range 90.000000" in caplog.text
    assert "average 95.000000" in caplog.text
    assert "median 95.000000" in caplog.text
    assert "standard deviation 28.722813" in caplog.text


def test_probe_accuracy_macro_sample_count(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    probe: ScanProbe[Sample],
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = ProbeAccuracyMacro(probe, toolhead)
    probe.probe_height = 2
    params.get_int = mocker.Mock(return_value=1)
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

    assert "probe accuracy results" in caplog.text
    assert "minimum 50.000000" in caplog.text
    assert "maximum 50.000000" in caplog.text
    assert "range 0.000000" in caplog.text
    assert "average 50.000000" in caplog.text
    assert "median 50.000000" in caplog.text
    assert "standard deviation 0.000000" in caplog.text


def test_query_probe_macro_triggered_output(
    caplog: LogCaptureFixture,
    endstop: ScanEndstop[object, Sample],
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = QueryProbe(endstop, toolhead)
    endstop.query_is_triggered = lambda print_time=...: True

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "probe: TRIGGERED" in caplog.text


def test_query_probe_macro_open_output(
    caplog: LogCaptureFixture,
    endstop: ScanEndstop[object, Sample],
    toolhead: Toolhead,
    params: MacroParams,
):
    macro = QueryProbe(endstop, toolhead)
    endstop.query_is_triggered = lambda print_time=...: False

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "probe: open" in caplog.text


def test_z_offset_apply_probe_output(caplog: LogCaptureFixture, toolhead: Toolhead, params: MacroParams):
    macro = ZOffsetApplyProbe(toolhead)
    toolhead.get_gcode_z_offset = lambda: -42.0

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "cartographer: z_offset: 42.000" in caplog.text
    assert "SAVE_CONFIG" in caplog.text
