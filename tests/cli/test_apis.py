from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_apis_no_args_lists_providers():
    """'mapi apis' with no arguments lists all providers (providers list)."""
    result = runner.invoke(app, ["apis"])
    assert result.exit_code == 0
    assert "pokeapi" in result.stdout
    assert "github" in result.stdout
    assert "Available Providers" in result.stdout


def test_apis_known_provider():
    """'mapi apis pokeapi' directly lists operations for pokeapi/REST."""
    result = runner.invoke(app, ["apis", "pokeapi"])
    assert result.exit_code == 0
    assert "Operations for pokeapi/REST" in result.stdout
    assert "pokemon_retrieve" in result.stdout


def test_apis_with_positional_filter():
    """'mapi apis pokeapi pokemon' filters pokeapi operations by 'pokemon'."""
    result = runner.invoke(app, ["apis", "pokeapi", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout
    assert "GET" in result.stdout


def test_apis_with_method_filter():
    """'mapi apis pokeapi -m get' filters pokeapi operations by HTTP method."""
    result = runner.invoke(app, ["apis", "pokeapi", "-m", "get"])
    assert result.exit_code == 0
    assert "GET" in result.stdout


def test_apis_composite_path():
    """'mapi apis pokeapi/REST pokemon' handles composite path syntax."""
    result = runner.invoke(app, ["apis", "pokeapi/REST", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout


def test_apis_unknown_provider():
    result = runner.invoke(app, ["apis", "nonexistent_provider"])
    assert result.exit_code != 0
