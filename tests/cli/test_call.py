from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_call_dry_run():
    result = runner.invoke(
        app, ["call", "pokeapi", "REST", "pokemon_retrieve", "id=ditto", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout
    assert "https://pokeapi.co/api/v2/pokemon/ditto/" in result.stdout


def test_call_composite_dry_run():
    result = runner.invoke(
        app, ["call", "pokeapi/REST/pokemon_retrieve", "id=ditto", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout
    assert "https://pokeapi.co/api/v2/pokemon/ditto/" in result.stdout


def test_call_curl():
    result = runner.invoke(
        app, ["call", "pokeapi", "REST", "pokemon_retrieve", "id=ditto", "--curl"]
    )
    assert result.exit_code == 0
    assert "curl -X GET 'https://pokeapi.co/api/v2/pokemon/ditto/'" in result.stdout
