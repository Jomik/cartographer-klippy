from __future__ import annotations

import inspect


def cleandoc(doc: str | None) -> str | None:
    if doc is None:
        return None
    return inspect.cleandoc(doc)


def format_macro(macro: str) -> str:
    return f'<a class="command">{macro}</a>'
