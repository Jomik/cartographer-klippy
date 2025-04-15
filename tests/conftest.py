from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from cartographer.printer_interface import MacroParams, Mcu, Position, Sample, Toolhead
from cartographer.stream import Session

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

collect_ignore: list[str] = []
if sys.version_info < (3, 9):
    # pytest-bdd 8.0.0 requires Python 3.9+
    collect_ignore.append("bdd")


@pytest.fixture
def toolhead(mocker: MockerFixture) -> Toolhead:
    mock = mocker.MagicMock(spec=Toolhead, autospec=True, instance=True)

    def get_requested_position(time: float) -> Position:
        return Position(x=0, y=0, z=time)

    mock.get_requested_position = get_requested_position

    return mock


@pytest.fixture
def session(mocker: MockerFixture) -> Session[Sample]:
    return Session(mocker.Mock(), mocker.Mock())


@pytest.fixture
def mcu(mocker: MockerFixture, session: Session[Sample]) -> Mcu[object, Sample]:
    mock = mocker.MagicMock(spec=Mcu, autospec=True, instance=True)
    mock.start_session = mocker.Mock(return_value=session)
    return mock


@pytest.fixture
def params(mocker: MockerFixture) -> MacroParams:
    return mocker.MagicMock(spec=MacroParams, autospec=True, instance=True)
