from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_describe_operation():
    result = runner.invoke(app, ["describe", "pokeapi", "REST", "pokemon_retrieve"])
    assert result.exit_code == 0
    assert "GET" in result.stdout
    assert "/api/v2/pokemon/{id}/" in result.stdout
    assert "id" in result.stdout
