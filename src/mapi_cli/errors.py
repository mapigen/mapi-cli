from __future__ import annotations

import difflib
import os
from collections.abc import Callable
from typing import Any

import click
from mapi.exceptions import (
    ConfigurationError,
    MapiError,
    RateLimitError,
    ServiceNotFoundError,
    TransportError,
    ValidationError,
)
from rich.console import Console

console_err = Console(stderr=True)

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_VALIDATION = 4
EXIT_CONFIG = 5
EXIT_TRANSPORT = 6
EXIT_HTTP_ERROR = 7
EXIT_RATE_LIMIT = 8
EXIT_INTERRUPT = 130


def suggest_close_matches(target: str, candidates: list[str] | tuple[str, ...]) -> str | None:
    """Find closest match in candidates for user suggestion."""
    matches = difflib.get_close_matches(target, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


def map_exception_to_exit_code(exc: Exception) -> int:
    """Map exceptions to standardized process exit codes."""
    if isinstance(exc, RateLimitError):
        return EXIT_RATE_LIMIT
    if isinstance(exc, TransportError):
        return EXIT_HTTP_ERROR if exc.http_status else EXIT_TRANSPORT
    if isinstance(exc, ValidationError):
        return EXIT_VALIDATION
    if isinstance(exc, ServiceNotFoundError):
        return EXIT_NOT_FOUND
    if isinstance(exc, ConfigurationError):
        return EXIT_CONFIG
    if isinstance(exc, (click.UsageError, click.BadParameter)):
        return EXIT_USAGE
    return EXIT_ERROR


def run(app_func: Callable[[], Any]) -> int:
    """Top-level CLI execution wrapper with standardized exit codes and rich error output."""
    try:
        res = app_func()
        return 0 if res is None else int(res)
    except KeyboardInterrupt:
        console_err.print("\n[yellow]Aborted by user.[/yellow]")
        return EXIT_INTERRUPT
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except ServiceNotFoundError as e:
        console_err.print(f"[bold red]Not Found Error:[/] {e}")
        return EXIT_NOT_FOUND
    except ValidationError as e:
        console_err.print(f"[bold red]Validation Error:[/] {e}")
        return EXIT_VALIDATION
    except RateLimitError as e:
        console_err.print(f"[bold red]Rate Limit Exceeded:[/] {e}")
        return EXIT_RATE_LIMIT
    except TransportError as e:
        status_info = f" (HTTP {e.http_status})" if e.http_status else ""
        console_err.print(f"[bold red]Transport Error{status_info}:[/] {e}")
        return EXIT_HTTP_ERROR if e.http_status else EXIT_TRANSPORT
    except ConfigurationError as e:
        console_err.print(f"[bold red]Configuration Error:[/] {e}")
        return EXIT_CONFIG
    except MapiError as e:
        console_err.print(f"[bold red]MAPI Error:[/] {e}")
        return EXIT_ERROR
    except Exception as e:
        if os.environ.get("MAPI_DEBUG") == "1":
            console_err.print_exception()
        else:
            console_err.print(f"[bold red]Error:[/] {e} (set MAPI_DEBUG=1 for full traceback)")
        return EXIT_ERROR
