from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_ops_list_and_filter():
    result = runner.invoke(app, ["ops", "pokeapi", "REST", "--filter", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout
    assert "GET" in result.stdout


def test_operations_alias():
    result = runner.invoke(app, ["operations", "pokeapi", "REST", "--filter", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout
    assert "GET" in result.stdout


def test_ops_lowercased_api():
    """Verify lowercased API names (e.g. 'rest' instead of 'REST') resolve cleanly."""
    result = runner.invoke(app, ["ops", "pokeapi", "rest", "--filter", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout
    assert "GET" in result.stdout
