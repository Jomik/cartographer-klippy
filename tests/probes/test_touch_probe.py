from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typing_extensions import TypeAlias

from cartographer.printer_interface import HomingState, Mcu, Sample, Toolhead
from cartographer.probes.touch_probe import Configuration, TouchProbe

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from cartographer.configuration import TouchModelConfiguration


Probe: TypeAlias = TouchProbe[object]


@pytest.fixture
def mcu(mocker: MockerFixture) -> Mcu[object, Sample]:
    return mocker.create_autospec(Mcu, instance=True)


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    return mocker.create_autospec(Toolhead, instance=True)


class MockConfiguration:
    x_offset: float = 0.0
    y_offset: float = 0.0
    move_speed: float = 42.0

    touch_retries: int = 0
    touch_samples: int = 5


class MockModel:
    name: str = "default"
    threshold: int = 5
    speed: float = 10.0
    z_offset: float = 0.0


@pytest.fixture
def config() -> Configuration:
    return MockConfiguration()


@pytest.fixture
def model() -> TouchModelConfiguration:
    return MockModel()


@pytest.fixture
def probe(mcu: Mcu[object, Sample], toolhead: Toolhead, config: Configuration, model: TouchModelConfiguration) -> Probe:
    return Probe(mcu, toolhead, config, model=model)


@pytest.fixture
def homing_state(mocker: MockerFixture, probe: Probe) -> HomingState:
    mock = mocker.Mock(spec=HomingState, autospec=True)
    mock.endstops = [probe]
    return mock


def test_probe_success(mocker: MockerFixture, toolhead: Toolhead, probe: Probe) -> None:
    toolhead.z_homing_move = mocker.Mock(return_value=0.5)

    assert probe.probe() == 0.5


def test_probe_standard_deviation_failure(mocker: MockerFixture, toolhead: Toolhead, probe: Probe) -> None:
    toolhead.z_homing_move = mocker.Mock(side_effect=[1.000, 1.002, 1.1, 1.016, 1.018])

    with pytest.raises(RuntimeError, match="failed"):
        _ = probe.probe()


def test_probe_suceeds_on_retry(
    mocker: MockerFixture, toolhead: Toolhead, probe: Probe, config: MockConfiguration
) -> None:
    config.touch_retries = 1
    toolhead.z_homing_move = mocker.Mock(side_effect=[1.0, 1.01, 1.5, 0.5, 0.5, 0.5, 0.5, 0.5])

    assert probe.probe() == 0.5


def test_probe_unhomed_z(mocker: MockerFixture, toolhead: Toolhead, probe: Probe) -> None:
    toolhead.is_homed = mocker.Mock(return_value=False)

    with pytest.raises(RuntimeError, match="Z axis must be homed"):
        _ = probe.probe()


def test_home_start_invalid_threshold(model: TouchModelConfiguration, probe: Probe) -> None:
    model.threshold = 0

    with pytest.raises(RuntimeError, match="threshold must be greater than 0"):
        _ = probe.home_start(print_time=0.0)


def test_home_wait(mocker: MockerFixture, mcu: Mcu[object, Sample], probe: Probe) -> None:
    mcu.stop_homing = mocker.Mock(return_value=1.5)

    assert probe.home_wait(home_end_time=1.0) == 1.5


def test_on_home_end(mocker: MockerFixture, probe: Probe, homing_state: HomingState) -> None:
    homed_position_spy = mocker.spy(homing_state, "set_z_homed_position")

    probe.on_home_end(homing_state)

    assert homed_position_spy.called == 1
