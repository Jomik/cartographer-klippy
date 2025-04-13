from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from cartographer.macros.probe import ZOffsetApplyProbeMacro
from cartographer.printer_interface import MacroParams, Position, Sample, Toolhead
from cartographer.probes.scan_probe import ScanProbe
from cartographer.probes.touch_probe import TouchProbe

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


@pytest.fixture
def scan_probe(mocker: MockerFixture):
    scan_probe = mocker.Mock(spec=ScanProbe, autospec=True)
    scan_probe.model = mocker.Mock()
    scan_probe.model.name = "test"
    scan_probe.offset = Position(0.0, 0.0, 0)
    return scan_probe


@pytest.fixture
def touch_probe(mocker: MockerFixture):
    touch_probe = mocker.Mock(spec=TouchProbe, autospec=True)
    touch_probe.model = None
    touch_probe.offset = Position(0.0, 0.0, 0)
    return touch_probe


def test_z_offset_apply_probe_output(
    caplog: LogCaptureFixture,
    toolhead: Toolhead,
    scan_probe: ScanProbe[object, Sample],
    touch_probe: TouchProbe[object],
    params: MacroParams,
):
    macro = ZOffsetApplyProbeMacro(toolhead, scan_probe, touch_probe)
    toolhead.get_gcode_z_offset = lambda: -42.0

    with caplog.at_level(logging.INFO):
        macro.run(params)

    assert "cartographer: scan test z_offset: 42" in caplog.text
    assert "SAVE_CONFIG" in caplog.text


def test_z_offset_apply_probe_scan(
    mocker: MockerFixture,
    toolhead: Toolhead,
    scan_probe: ScanProbe[object, Sample],
    touch_probe: TouchProbe[object],
    params: MacroParams,
):
    scan_z_offset_spy = mocker.spy(scan_probe, "save_z_offset")
    touch_z_offset_spy = mocker.spy(touch_probe, "save_z_offset")
    macro = ZOffsetApplyProbeMacro(toolhead, scan_probe, touch_probe)
    # Move 1 up from the bed
    toolhead.get_gcode_z_offset = lambda: 1.0

    macro.run(params)
    # A positive gcode_z_offset means that our probe moves closer to the nozzle
    assert scan_z_offset_spy.mock_calls == [mocker.call(-1.0)]
    assert touch_z_offset_spy.mock_calls == []


def test_z_offset_apply_probe_touch(
    mocker: MockerFixture,
    toolhead: Toolhead,
    scan_probe: ScanProbe[object, Sample],
    touch_probe: TouchProbe[object],
    params: MacroParams,
):
    model = mocker.Mock()
    touch_probe.model = model
    scan_z_offset_spy = mocker.spy(scan_probe, "save_z_offset")
    touch_z_offset_spy = mocker.spy(touch_probe, "save_z_offset")
    macro = ZOffsetApplyProbeMacro(toolhead, scan_probe, touch_probe)
    # Move 1 up from the bed
    toolhead.get_gcode_z_offset = lambda: 1.0

    macro.run(params)
    # A positive gcode_z_offset means that our probe moves closer to the nozzle
    assert touch_z_offset_spy.mock_calls == [mocker.call(-1.0)]
    assert scan_z_offset_spy.mock_calls == []
