from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import typer
from rich import box
from rich.panel import Panel

from mapi_cli.ui.console import console

completion_app = typer.Typer(
    name="completion",
    help="Configure and install fast terminal tab autocompletion (Bash, Zsh, Fish).",
    no_args_is_help=False,
)

SupportedShell = Literal["bash", "zsh", "fish", "powershell"]


def detect_shell() -> SupportedShell:
    """Detect current user shell from environment."""
    shell_env = os.environ.get("SHELL", "").lower()
    if "zsh" in shell_env:
        return "zsh"
    if "fish" in shell_env:
        return "fish"
    if "powershell" in shell_env or "pwsh" in shell_env:
        return "powershell"
    return "bash"


def get_completion_snippet(shell: SupportedShell) -> str:
    """Generate shell-specific hook snippet for instant dynamic completion."""
    if shell == "bash":
        return 'eval "$(_MAPI_COMPLETE=bash_source mapi)"'
    if shell == "zsh":
        return 'eval "$(_MAPI_COMPLETE=zsh_source mapi)"'
    if shell == "fish":
        return "eval (env _MAPI_COMPLETE=fish_source mapi)"
    if shell == "powershell":
        return 'Register-ArgumentCompleter -Native -CommandName mapi -ScriptBlock { param($wordToComplete, $commandAst, $cursorPosition) [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new(); $env:_MAPI_COMPLETE = "powershell_complete"; mapi $wordToComplete | ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, "ParameterValue", $_) } }'
    return 'eval "$(_MAPI_COMPLETE=bash_source mapi)"'


@completion_app.callback(invoke_without_command=True)
def completion_default(ctx: typer.Context) -> None:
    """Show shell completion status and quick install guide when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        shell = detect_shell()
        snippet = get_completion_snippet(shell)
        console.print(
            Panel(
                f"[bold cyan]Detected Shell:[/] [bold green]{shell}[/]\n\n"
                f"[bold]To activate tab completion in your current session:[/]\n"
                f"  [yellow]{snippet}[/]\n\n"
                f"[bold]To permanently install tab completion, run:[/]\n"
                f"  [bold green]mapi completion install[/]",
                title="Terminal Tab Completion",
                box=box.ROUNDED,
            )
        )


@completion_app.command("show")
def show_completion(
    shell: SupportedShell | None = typer.Argument(
        None, help="Target shell (bash, zsh, fish, powershell)"
    ),
) -> None:
    """Print the completion activation snippet for evaluation in your shell."""
    target_shell = shell or detect_shell()
    typer.echo(get_completion_snippet(target_shell))


@completion_app.command("install")
def install_completion(
    shell: SupportedShell | None = typer.Argument(
        None, help="Target shell (bash, zsh, fish, powershell)"
    ),
) -> None:
    """Automatically append completion hook to shell configuration file."""
    target_shell = shell or detect_shell()
    snippet = get_completion_snippet(target_shell)
    home = Path.home()

    rc_file: Path | None = None
    if target_shell == "bash":
        rc_file = home / ".bashrc"
    elif target_shell == "zsh":
        rc_file = home / ".zshrc"
    elif target_shell == "fish":
        completions_dir = home / ".config" / "fish" / "completions"
        completions_dir.mkdir(parents=True, exist_ok=True)
        rc_file = completions_dir / "mapi.fish"

    if rc_file is None:
        console.print(
            f"[bold yellow]Automatic install not supported for {target_shell}.[/]\n"
            f"Add this snippet to your shell profile:\n  {snippet}"
        )
        return

    # Check if already installed
    comment_header = "# MAPI CLI Autocompletion"
    already_installed = False
    if rc_file.exists():
        content = rc_file.read_text(encoding="utf-8")
        if "_MAPI_COMPLETE=" in content or comment_header in content:
            already_installed = True

    if not already_installed:
        try:
            with open(rc_file, "a", encoding="utf-8") as f:
                f.write(f"\n{comment_header}\n{snippet}\n")
            console.print(
                Panel(
                    f"[bold green]Tab autocompletion installed successfully![/]\n\n"
                    f"[bold]Updated config:[/] [cyan]{rc_file}[/]\n"
                    f"[bold]Activation:[/]     Run [yellow]source {rc_file}[/] or open a new terminal window.",
                    title="Installation Complete",
                    box=box.ROUNDED,
                )
            )
        except Exception as e:
            console.print(f"[bold red]Failed to write to {rc_file}:[/] {e}")
            raise typer.Exit(1) from e
    else:
        console.print(
            f"[bold green]Autocompletion is already configured in[/] [cyan]{rc_file}[/].\n"
            f"[dim]If completion isn't working, run:[/] [yellow]source {rc_file}[/]"
        )
