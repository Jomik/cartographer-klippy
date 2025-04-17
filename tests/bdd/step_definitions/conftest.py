from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, then
from typing_extensions import override

from cartographer.printer_interface import MacroParams

if TYPE_CHECKING:
    from pytest import LogCaptureFixture


@pytest.fixture
def params() -> MacroParams:
    return MockParams()


class MockParams(MacroParams):
    def __init__(self) -> None:
        self.params: dict[str, str] = {}

    @override
    def get(self, name: str, default: str = ...) -> str:
        return str(self.params.get(name, default))

    @override
    def get_float(self, name: str, default: float = ..., *, above: float = ..., minval: float = ...) -> float:
        return float(self.params.get(name, default))

    @override
    def get_int(self, name: str, default: int = ..., *, minval: int = ..., maxval: int = ...) -> int:
        return int(self.params.get(name, default))


@given("macro parameters:")
def given_parameters(datatable: list[list[str]], params: MockParams):
    params.params = {key: value for key, value in datatable}


@then(parsers.parse('it should log "{output}"'))
def then_log_result(caplog: LogCaptureFixture, output: str):
    assert output in caplog.text
