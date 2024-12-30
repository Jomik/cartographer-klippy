import inspect
from typing import Optional


def cleandoc(doc: Optional[str]) -> Optional[str]:
    if doc is None:
        return None
    return inspect.cleandoc(doc)
