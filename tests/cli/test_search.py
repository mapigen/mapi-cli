from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_search():
    result = runner.invoke(app, ["search", "pokemon"])
    assert result.exit_code == 0
    assert "Search Results for 'pokemon'" in result.stdout
    assert "pokemon_retrieve" in result.stdout
