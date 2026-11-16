from __future__ import annotations

import pytest
from mapi import Mapi
from textual.widgets import DataTable, Input

from mapi_cli.paths import resolve_data_dir
from mapi_cli.ui.download_tui import DownloadTUIApp


@pytest.mark.asyncio
async def test_download_tui_navigation_and_filter():
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)
    app = DownloadTUIApp(client=client, data_dir=data_dir)

    async with app.run_test() as pilot:
        table = pilot.app.query_one("#providers_table", DataTable)
        assert table.row_count >= 5

        # Test Arrow Navigation (Down / Up)
        await pilot.press("down")
        assert table.cursor_coordinate.row == 1
        await pilot.press("up")
        assert table.cursor_coordinate.row == 0

        # Test Toggle Force
        assert app.force is False
        await pilot.press("f")
        assert app.force is True
        await pilot.press("f")
        assert app.force is False

        # Test Toggle Theme
        assert app.is_dark is True
        await pilot.press("t")
        assert app.is_dark is False
        assert "light-mode" in app.screen.classes
        await pilot.press("t")
        assert app.is_dark is True

        # Test Filter / Search Input
        await pilot.press("slash")
        input_widget = pilot.app.query_one("#filter_input", Input)
        assert input_widget.has_focus

        input_widget.value = "stripe"
        await pilot.pause()
        assert table.row_count == 1

        # Clear Filter
        input_widget.value = ""
        await pilot.pause()
        assert table.row_count >= 5

        # Test loader display toggles without 'str object has no attribute value' error
        app.set_loading(True)
        assert app.query_one("#loader").styles.display == "block"
        app.set_loading(False)
        assert app.query_one("#loader").styles.display == "none"

        # Test Pressing Enter on selected row
        await pilot.press("enter")
        await pilot.pause()

        # Test Quit
        await pilot.press("q")
