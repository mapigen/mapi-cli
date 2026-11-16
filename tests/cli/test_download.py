from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_download_help():
    result = runner.invoke(app, ["download", "--help"])
    assert result.exit_code == 0
    assert "Download and compile remote API specifications" in result.stdout
    assert "--all" in result.stdout


def test_download_already_downloaded():
    result = runner.invoke(app, ["download", "pokeapi"])
    assert result.exit_code == 0
    assert "pokeapi" in result.stdout
    assert "Skipped" in result.stdout


def test_download_json_output():
    result = runner.invoke(app, ["-o", "json", "download", "pokeapi"])
    assert result.exit_code == 0
    assert '"status":"skipped"' in result.stdout
    assert '"provider":"pokeapi"' in result.stdout


def test_download_unknown_provider():
    result = runner.invoke(app, ["download", "nonexistent_provider"])
    assert result.exit_code == 1
    assert "No APIs found" in result.stdout
