from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler

console_err = Console(stderr=True)


def configure_logging(verbose: int = 0, quiet: bool = False) -> None:
    """Configure CLI application logging to stderr using RichHandler."""
    if quiet:
        level = logging.ERROR
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console_err, rich_tracebacks=True, show_path=False)],
        force=True,
    )
