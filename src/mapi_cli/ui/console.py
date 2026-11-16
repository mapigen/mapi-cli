from __future__ import annotations

from rich.console import Console

from mapi_cli.ui.theme import MAPI_THEME

# Standard output console for data only (dynamic sys.stdout for test runner compatibility)
console = Console(theme=MAPI_THEME)

# Standard error console for logs, warnings, errors, and interactive status
console_err = Console(theme=MAPI_THEME, stderr=True)
