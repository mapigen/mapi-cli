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


def test_ops_single_argument_auto_resolves_api():
    """'mapi ops pokeapi' automatically resolves the single 'REST' API."""
    result = runner.invoke(app, ["ops", "pokeapi"])
    assert result.exit_code == 0
    assert "Operations for pokeapi/REST" in result.stdout
    assert "pokemon_retrieve" in result.stdout


def test_ops_positional_query_two_args():
    """'mapi ops pokeapi pokemon' resolves REST and filters by pokemon."""
    result = runner.invoke(app, ["ops", "pokeapi", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout


def test_ops_positional_query_three_args():
    """'mapi ops pokeapi REST pokemon' passes positional filter without error."""
    result = runner.invoke(app, ["ops", "pokeapi", "REST", "pokemon"])
    assert result.exit_code == 0
    assert "pokemon_retrieve" in result.stdout


def test_ops_method_filter():
    """'mapi ops pokeapi -m get' filters by HTTP method."""
    result = runner.invoke(app, ["ops", "pokeapi", "-m", "get"])
    assert result.exit_code == 0
    assert "GET" in result.stdout


def test_ops_method_positional_query():
    """'mapi ops pokeapi get' treats 'get' as method filter."""
    result = runner.invoke(app, ["ops", "pokeapi", "get"])
    assert result.exit_code == 0
    assert "GET" in result.stdout


def test_ops_method_no_match():
    """'mapi ops pokeapi -m post' prints friendly message when no operations match method."""
    result = runner.invoke(app, ["ops", "pokeapi", "-m", "post"])
    assert result.exit_code == 0
    assert "No operations found" in result.stdout
