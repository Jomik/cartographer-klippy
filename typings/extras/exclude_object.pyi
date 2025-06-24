from typing import TypedDict

from typing_extensions import NotRequired

class _PrinterObject(TypedDict):
    name: str
    center: NotRequired[list[float]]
    polygon: NotRequired[list[list[float]]]

class _Status(TypedDict):
    objects: list[_PrinterObject]
    excluded_objects: list[_PrinterObject]
    current_object: _PrinterObject | None

class ExcludeObject:
    def get_status(self, eventtime: float | None = ...) -> _Status: ...
