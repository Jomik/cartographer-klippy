from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from typing_extensions import TypeAlias

from cartographer.macros.bed_mesh import BedMeshCalibrateMacro, Configuration, MeshHelper, MeshPoint
from cartographer.printer_interface import MacroParams, Position, Toolhead
from cartographer.probes.scan_probe import Model, ScanProbe
from cartographer.stream import Session

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@dataclass
class Sample:
    time: float
    frequency: float


Probe: TypeAlias = ScanProbe[object, Sample]
Macro: TypeAlias = BedMeshCalibrateMacro[MacroParams]
Helper: TypeAlias = MeshHelper[MacroParams]


@pytest.fixture
def model(mocker: MockerFixture) -> Model:
    return mocker.MagicMock(spec=Model, autospec=True, instance=True)


@pytest.fixture
def session(mocker: MockerFixture) -> Session[Sample]:
    return Session[Sample](mocker.Mock(), mocker.Mock())


@pytest.fixture
def probe(mocker: MockerFixture, model: Model, session: Session[Sample]) -> Probe:
    probe = mocker.MagicMock(spec=ScanProbe, autospec=True, instance=True)
    probe.model = model
    probe.z_offset = 1.5
    probe.probe_height = 10.0
    probe.start_session = mocker.Mock(return_value=session)
    return probe


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.MagicMock(spec=Toolhead, autospec=True, instance=True)


@pytest.fixture
def helper(mocker: MockerFixture) -> Helper:
    return mocker.MagicMock(spec=MeshHelper, autospec=True, instance=True)


@pytest.fixture
def config(mocker: MockerFixture) -> Configuration:
    config = mocker.MagicMock(spec=Configuration, autospec=True, instance=True)
    config.speed = 400
    config.scan_height = 5.0
    config.x_offset = 0.0
    config.y_offset = 0.0
    return config


@pytest.fixture
def macro(probe: Probe, toolhead: Toolhead, helper: Helper, config: Configuration) -> Macro:
    return BedMeshCalibrateMacro(probe, toolhead, helper, config)


def test_run_valid_scan(mocker: MockerFixture, macro: Macro, toolhead: Toolhead, helper: Helper):
    helper.generate_path = mocker.Mock(return_value=[MeshPoint(10, 10, False), MeshPoint(20, 20, False)])
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="scan")
    params.get_float = mocker.Mock(return_value=42.0)
    prepare_spy = mocker.spy(helper, "prepare")
    move_spy = mocker.spy(toolhead, "manual_move")
    finalize_spy = mocker.spy(helper, "finalize")

    macro.run(params)

    assert prepare_spy.call_count == 1
    assert [
        mocker.call(x=10, y=10, speed=42.0),
        mocker.call(x=20, y=20, speed=42.0),
    ] in move_spy.mock_calls
    assert finalize_spy.call_count == 1


def test_applies_offsets(
    mocker: MockerFixture,
    macro: Macro,
    toolhead: Toolhead,
    helper: Helper,
    config: Configuration,
):
    helper.generate_path = mocker.Mock(return_value=[MeshPoint(10, 10, False), MeshPoint(20, 20, False)])
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="scan")
    params.get_float = mocker.Mock(return_value=42.0)
    config.x_offset = -5
    config.y_offset = 5
    move_spy = mocker.spy(toolhead, "manual_move")

    macro.run(params)

    assert [
        mocker.call(x=15, y=5, speed=42.0),
        mocker.call(x=25, y=15, speed=42.0),
    ] in move_spy.mock_calls


def test_multiple_runs(
    mocker: MockerFixture,
    macro: Macro,
    toolhead: Toolhead,
    helper: Helper,
):
    helper.generate_path = mocker.Mock(return_value=[MeshPoint(10, 10, False), MeshPoint(20, 20, False)])
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="scan")
    params.get_int = mocker.Mock(return_value=3)
    params.get_float = mocker.Mock(return_value=42.0)
    move_spy = mocker.spy(toolhead, "manual_move")

    macro.run(params)

    assert [
        # first
        mocker.call(x=10, y=10, speed=42.0),
        mocker.call(x=20, y=20, speed=42.0),
        # second
        mocker.call(x=20, y=20, speed=42.0),
        mocker.call(x=10, y=10, speed=42.0),
        # third
        mocker.call(x=10, y=10, speed=42.0),
        mocker.call(x=20, y=20, speed=42.0),
    ] in move_spy.mock_calls


def test_run_invalid_method(mocker: MockerFixture, macro: Macro, helper: Helper):
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="invalid")
    prepare_spy = mocker.spy(helper, "prepare")
    orig_macro_spy = mocker.spy(helper, "orig_macro")
    finalize_spy = mocker.spy(helper, "finalize")

    macro.run(params)
    assert orig_macro_spy.call_count == 1
    assert prepare_spy.call_count == 0
    assert finalize_spy.call_count == 0


def test_calculate_positions_no_valid_samples(
    mocker: MockerFixture,
    macro: Macro,
    model: Model,
    toolhead: Toolhead,
    helper: Helper,
    session: Session[Sample],
):
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="scan")
    helper.generate_path = mocker.Mock(return_value=[MeshPoint(10, 10, True)])
    model.frequency_to_distance = mocker.Mock(return_value=float("nan"))
    toolhead.get_requested_position = mocker.Mock(return_value=Position(10, 10, 5))
    session.get_items = lambda: [Sample(time=0.0, frequency=100) for _ in range(2)]

    with pytest.raises(RuntimeError, match="no valid samples"):
        macro.run(params)


def test_calculate_positions_cluster_no_samples(
    mocker: MockerFixture,
    macro: Macro,
    model: Model,
    toolhead: Toolhead,
    helper: Helper,
    session: Session[Sample],
):
    params = mocker.MagicMock()
    params.get = mocker.Mock(return_value="scan")
    helper.generate_path = mocker.Mock(return_value=[MeshPoint(10, 10, True), MeshPoint(20, 20, True)])
    model.frequency_to_distance = mocker.Mock(return_value=1)
    toolhead.get_requested_position = mocker.Mock(return_value=Position(10, 10, 5))
    session.get_items = lambda: [Sample(time=0.0, frequency=100) for _ in range(2)]

    with pytest.raises(RuntimeError, match="no samples"):
        macro.run(params)
