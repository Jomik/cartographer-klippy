from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pytest_bdd import given, parsers, scenarios, then, when

if TYPE_CHECKING:
    from pytest import LogCaptureFixture

    from cartographer.interfaces.configuration import Configuration
    from cartographer.interfaces.printer import MacroParams, Toolhead
    from cartographer.probe import Probe
    from tests.bdd.helpers.context import Context


scenarios("../../features/z_offset.feature")


@given(parsers.parse("I have baby stepped the nozzle {offset:g}mm up"))
def given_baby_step_up(toolhead: Toolhead, offset: float):
    toolhead.get_gcode_z_offset = lambda: offset


@given(parsers.parse("I have baby stepped the nozzle {offset:g}mm down"))
def given_baby_step_down(toolhead: Toolhead, offset: float):
    toolhead.get_gcode_z_offset = lambda: -offset


@when("I run the Z_OFFSET_APPLY_PROBE macro")
def when_run_probe_accuracy_macro(
    params: MacroParams,
    caplog: LogCaptureFixture,
    probe: Probe,
    toolhead: Toolhead,
    config: Configuration,
    context: Context,
):
    from cartographer.macros.probe import ZOffsetApplyProbeMacro

    macro = ZOffsetApplyProbeMacro(probe, toolhead, config)
    with caplog.at_level(logging.INFO):
        try:
            macro.run(params)
        except Exception as e:
            context.error = e


@then(parsers.parse("it should set scan z-offset to {offset:g}"))
def then_update_scan_z_offset(config: Configuration, offset: str):
    assert config.scan.models["default"].z_offset == float(offset)


@then(parsers.parse("it should set touch z-offset to {offset:g}"))
def then_update_touch_z_offset(config: Configuration, offset: str):
    assert config.touch.models["default"].z_offset == float(offset)
