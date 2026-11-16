from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_search():
    result = runner.invoke(app, ["search", "pokemon"])
    assert result.exit_code == 0
    assert "Search Results for 'pokemon'" in result.stdout
    assert "pokemon_retrieve" in result.stdout


def test_search_with_method_filter():
    result = runner.invoke(app, ["search", "pokemon", "-m", "get"])
    assert result.exit_code == 0
    assert "Search Results for 'pokemon'" in result.stdout
    assert "pokemon_retrieve" in result.stdout
    assert "GET" in result.stdout


def test_search_method_query():
    result = runner.invoke(app, ["search", "get"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout
