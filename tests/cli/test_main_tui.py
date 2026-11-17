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
        assert input_widget.value.startswith(("/call", "/apis"))

        # Execute /theme via command palette
        input_widget.value = "/theme"
        await pilot.press("enter")
        await pilot.pause()
        assert app.is_dark is False


@pytest.mark.asyncio
async def test_main_tui_call_and_requirements():
    """Verify operation requirements inspection, call shortcut 'c', and /call execution in TUI."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = MapiTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        # Enter operations view for pokeapi
        await pilot.press("enter")
        await pilot.pause()
        assert app.current_view == "operations"

        # Highlight ability_retrieve (row 2 in pokeapi REST)
        table = pilot.app.query_one("#catalog_table", DataTable)
        table.move_cursor(row=2)
        await pilot.pause()

        # Press 'i' to inspect requirements
        await pilot.press("i")
        await pilot.pause()
        status_text = pilot.app.query_one("#status_text")
        render_str = str(status_text.render())
        assert "ID:" in render_str
        assert "Req:" in render_str

        # Press 'c' to initiate call (should detect missing 'id' and prefill /call id=)
        await pilot.press("c")
        await pilot.pause()
        input_widget = pilot.app.query_one("#command_input", Input)
        assert input_widget.has_focus
        assert "/call id=" in input_widget.value

        # Test dry-run command
        input_widget.value = "/dry-run id=1"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert "Dry-Run" in str(status_text.render())

        # Test curl command
        input_widget.focus()
        input_widget.value = "/curl id=1"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert "curl" in str(status_text.render()).lower()

        # Test call rejection when required arguments are missing
        input_widget.focus()
        input_widget.value = "/call"
        await pilot.press("enter")
        await pilot.pause()
        assert "Cannot Call:" in str(status_text.render())
        assert "Missing argument(s)" in str(status_text.render())


@pytest.mark.asyncio
async def test_main_tui_page_navigation_and_cursor_isolation():
    """Verify up/down cursor isolation, left/right horizontal neutrality, and ctrl+left/ctrl+right page navigation."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = MapiTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        table = pilot.app.query_one("#catalog_table", DataTable)
        assert app.current_view == "providers"

        # 1. Verify Up / Down stays cursor navigation (does not change view/page)
        initial_row = table.cursor_coordinate.row
        await pilot.press("down")
        await pilot.pause()
        assert table.cursor_coordinate.row == initial_row + 1
        assert app.current_view == "providers"

        await pilot.press("up")
        await pilot.pause()
        assert table.cursor_coordinate.row == initial_row
        assert app.current_view == "providers"

        # 2. Verify plain Left / Right does NOT navigate pages
        await pilot.press("right")
        await pilot.pause()
        assert app.current_view == "providers"

        await pilot.press("left")
        await pilot.pause()
        assert app.current_view == "providers"

        # 3. Ctrl+Right in providers view navigates forward into operations for selected API (pokeapi)
        await pilot.press("ctrl+right")
        await pilot.pause()
        assert app.current_view == "operations"
        assert app.selected_provider == "pokeapi"
        assert app.page_number == 1
        assert app.total_pages == 5  # pokeapi has 102 ops, 25 per page = 5 pages
        assert table.row_count == 25

        # 4. In operations view, Up / Down stays cursor navigation
        op_initial_row = table.cursor_coordinate.row
        await pilot.press("down")
        await pilot.pause()
        assert table.cursor_coordinate.row == op_initial_row + 1
        assert app.page_number == 1

        # 5. Ctrl+Right in operations navigates forward to Page 2
        await pilot.press("ctrl+right")
        await pilot.pause()
        assert app.page_number == 2
        assert table.row_count == 25  # page 2 has 25 items (items 26-50)

        # 6. Ctrl+Left in operations navigates back to Page 1
        await pilot.press("ctrl+left")
        await pilot.pause()
        assert app.page_number == 1
        assert table.row_count == 25

        # 7. Ctrl+Left on Page 1 navigates back to Providers & APIs catalog
        await pilot.press("ctrl+left")
        await pilot.pause()
        assert app.current_view == "providers"
        assert table.row_count >= 5

        # 8. Test /next and /prev slash commands
        input_widget = pilot.app.query_one("#command_input", Input)
        input_widget.focus()
        input_widget.value = "/next"
        await pilot.press("enter")
        await pilot.pause()
        assert app.current_view == "operations"

        input_widget.focus()
        input_widget.value = "/next"
        await pilot.press("enter")
        await pilot.pause()
        assert app.page_number == 2

        input_widget.focus()
        input_widget.value = "/prev"
        await pilot.press("enter")
        await pilot.pause()
        assert app.page_number == 1


