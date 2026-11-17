from __future__ import annotations

import pytest
from mapi import Mapi
from textual.widgets import DataTable, Input, OptionList

from mapi_cli.paths import resolve_data_dir
from mapi_cli.ui.banner import MAPI_ASCII_ART, render_banner
from mapi_cli.ui.command_palette import filter_commands
from mapi_cli.ui.main_tui import MapiTUIApp


def test_banner_rendering():
    """Verify Celadon Green text art banner renders with both dark and light palettes."""
    dark_banner = render_banner(is_dark=True)
    assert len(MAPI_ASCII_ART) > 50
    assert "Universal API Discovery Engine" in dark_banner.plain
    assert "--no-tui" in dark_banner.plain

    light_banner = render_banner(is_dark=False)
    assert "Universal API Discovery Engine" in light_banner.plain


def test_command_palette_filtering():
    """Verify intelligent '/' based command filtering as user types."""
    # Root slash should return all default commands
    all_cmds = filter_commands("/")
    assert len(all_cmds) >= 7

    # Filter by prefix
    apis_cmds = filter_commands("/ap")
    assert any(c.command == "/apis" for c in apis_cmds)

    # Filter by alias
    dl_cmds = filter_commands("/sync")
    assert any(c.command == "/download" for c in dl_cmds)

    # Filter by theme
    theme_cmds = filter_commands("/th")
    assert any(c.command == "/theme" for c in theme_cmds)


@pytest.mark.asyncio
async def test_main_tui_app_lifecycle_and_theme():
    """Verify MapiTUIApp mounts, navigates, and toggles Celadon themes."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = MapiTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        table = pilot.app.query_one("#catalog_table", DataTable)
        assert table.row_count >= 5

        # Check theme toggle (default dark -> light -> dark)
        assert app.is_dark is True
        await pilot.press("t")
        assert app.is_dark is False
        assert "light-mode" in app.screen.classes

        await pilot.press("t")
        assert app.is_dark is True
        assert "light-mode" not in app.screen.classes

        # Test '/' command palette focus
        await pilot.press("slash")
        input_widget = pilot.app.query_one("#command_input", Input)
        assert input_widget.has_focus
        assert input_widget.value.startswith("/")

        # Type '/th' and check suggestions appear
        input_widget.value = "/th"
        await pilot.pause()
        suggestions_container = pilot.app.query_one("#suggestions_container")
        assert suggestions_container.styles.display == "block"

        # Press Escape to dismiss
        await pilot.press("escape")
        await pilot.pause()
        assert suggestions_container.styles.display == "none"
        assert table.has_focus

        # Quit
        await pilot.press("q")


@pytest.mark.asyncio
async def test_main_tui_operations_view_and_inspection():
    """Verify entering operations view, inspecting operation, filtering, and returning."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = MapiTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        table = pilot.app.query_one("#catalog_table", DataTable)
        assert app.current_view == "providers"

        # Press Enter on the first row (pokeapi)
        await pilot.press("enter")
        await pilot.pause()
        assert app.current_view == "operations"
        assert table.row_count > 0

        # Press Enter to inspect operation
        await pilot.press("enter")
        await pilot.pause()
        status_text = pilot.app.query_one("#status_text")
        assert "ID:" in str(status_text.render())

        # Test filtering operations
        sample_term = app._current_operations[0]["id"][:4]
        input_widget = pilot.app.query_one("#command_input", Input)
        input_widget.focus()
        input_widget.value = sample_term
        await pilot.pause()
        assert table.row_count > 0

        # Press 'b' to return to catalog
        table.focus()
        await pilot.press("b")
        await pilot.pause()
        assert app.current_view == "providers"
        assert table.row_count >= 5


@pytest.mark.asyncio
async def test_command_palette_arrow_nav_and_execute():
    """Verify arrow navigation, tab completion, and command execution in palette."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = MapiTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        input_widget = pilot.app.query_one("#command_input", Input)
        input_widget.focus()
        input_widget.value = "/"
        await pilot.pause()

        opt_list = pilot.app.query_one("#suggestions_list", OptionList)
        assert opt_list.highlighted == 0

        # Navigate down
        await pilot.press("down")
        assert opt_list.highlighted == 1

        # Navigate up
        await pilot.press("up")
        assert opt_list.highlighted == 0

        # Tab completion
        await pilot.press("tab")
        assert input_widget.value.startswith("/apis")

        # Execute /theme via command palette
        input_widget.value = "/theme"
        await pilot.press("enter")
        await pilot.pause()
        assert app.is_dark is False
