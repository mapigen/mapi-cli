from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_providers_table():
    result = runner.invoke(app, ["providers"])
    assert result.exit_code == 0
    assert "pokeapi" in result.stdout
    assert "github" in result.stdout


def test_providers_json():
    result = runner.invoke(app, ["-o", "json", "providers"])
    assert result.exit_code == 0
    assert '"provider":"pokeapi"' in result.stdout


def test_providers_hidden_from_help():
    """Verify 'providers' is hidden from root --help, while 'apis' is present."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "apis" in result.stdout
    assert "List all available API providers" not in result.stdout
