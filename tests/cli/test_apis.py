from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_apis_known_provider():
    result = runner.invoke(app, ["apis", "pokeapi"])
    assert result.exit_code == 0
    assert "REST" in result.stdout


def test_apis_unknown_provider():
    result = runner.invoke(app, ["apis", "nonexistent_provider"])
    assert result.exit_code != 0
