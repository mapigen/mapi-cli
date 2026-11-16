from __future__ import annotations

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System & MAPI Doctor" in result.stdout
    assert "PASS" in result.stdout
