from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from cartographer.printer_interface import MacroParams

T = TypeVar("T", bound=Enum)


def get_enum_choice(params: MacroParams, option: str, enum_type: type[T], default: T) -> T:
    choice = params.get(option, default=default.value)

    # Convert both the choice and enum values to lowercase for case-insensitive comparison
    lower_choice = str(choice).lower()
    lower_mapping = {str(v.value).lower(): v for v in enum_type}

    if lower_choice not in lower_mapping:
        msg = f"invalid choice '{choice}' for option '{option}'"
        raise RuntimeError(msg)

    return lower_mapping[lower_choice]
