from __future__ import annotations

import itertools
import logging
import sys
from typing import TYPE_CHECKING, cast

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cartographer.printer_interface import MacroParams, Probe, Toolhead

if TYPE_CHECKING:
    from unittest.mock import Mock

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

pytestmark = pytest.mark.skipif(sys.version_info < (3, 9), reason="requires Python 3.9+")
scenarios("../../features/probe.feature")


@given("a probe", target_fixture="probe")
def given_probe(mocker: MockerFixture) -> Probe:
    mock = mocker.MagicMock(spec=Probe, autospec=True)
    return mock


@given("the probe measures:")
def given_probe_measurements(mocker: MockerFixture, probe: Probe, datatable: list[list[str]]):
    probe.probe = mocker.Mock(side_effect=itertools.cycle(map(float, itertools.chain.from_iterable(datatable))))


@given("the probe is triggered")
def given_probe_triggered(mocker: MockerFixture, probe: Probe):
    probe.query_is_triggered = mocker.Mock(return_value=True)


@given("the probe is not triggered")
def given_probe_not_triggered(mocker: MockerFixture, probe: Probe):
    probe.query_is_triggered = mocker.Mock(return_value=False)


@when("I run the PROBE macro")
def when_run_probe_macro(params: MacroParams, caplog: LogCaptureFixture, probe: Probe):
    from cartographer.macros.probe import ProbeMacro

    macro = ProbeMacro(probe)
    with caplog.at_level(logging.INFO):
        macro.run(params)


@when("I run the PROBE_ACCURACY macro")
def when_run_probe_accuracy_macro(params: MacroParams, caplog: LogCaptureFixture, probe: Probe, toolhead: Toolhead):
    from cartographer.macros.probe import ProbeAccuracyMacro

    macro = ProbeAccuracyMacro(probe, toolhead)
    with caplog.at_level(logging.INFO):
        macro.run(params)


@when("I run the QUERY_PROBE macro")
def when_run_query_probe_macro(params: MacroParams, caplog: LogCaptureFixture, probe: Probe, toolhead: Toolhead):
    from cartographer.macros.probe import QueryProbeMacro

    macro = QueryProbeMacro(probe, toolhead)
    with caplog.at_level(logging.INFO):
        macro.run(params)


@then(parsers.parse("it should probe {count:d} times"))
def then_probe_count(probe: Probe, count: int):
    assert cast("Mock", probe.probe).call_count == count
