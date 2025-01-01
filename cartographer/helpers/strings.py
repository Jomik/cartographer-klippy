import inspect
from typing import Optional


def cleandoc(doc: Optional[str]) -> Optional[str]:
    if doc is None:
        return None
    return inspect.cleandoc(doc)


def format_macro(macro: str) -> str:
    return f'<a class="command">{macro}</a>'
