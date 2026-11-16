from __future__ import annotations

from typing import Any

from mapi.models.domain import Operation, Parameter
from rich.prompt import Prompt


def prompt_for_parameters(op: Operation) -> dict[str, Any]:
    """Interactively prompt user for required and optional parameters."""
    params: dict[str, Any] = {}
    for p in op.parameters:
        if isinstance(p, Parameter):
            prompt_text = f"Parameter '{p.name}' ({p.in_})"
            if p.required:
                val = Prompt.ask(f"[bold red]{prompt_text}*[/]")
                params[p.name] = val
            else:
                val = Prompt.ask(f"[dim]{prompt_text}[/]", default="")
                if val:
                    params[p.name] = val
    return params
