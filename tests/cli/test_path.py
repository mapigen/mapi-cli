from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mapi_cli.app import app

runner = CliRunner()


def test_path_show():
    result = runner.invoke(app, ["path"])
    assert result.exit_code == 0
    assert "MAPI Path & Environment Status" in result.stdout
    assert "Core MAPI SDK" in result.stdout
    assert "Data Directory" in result.stdout


def test_path_find():
    result = runner.invoke(app, ["path", "find"])
    assert result.exit_code == 0
    assert "MAPI Path Auto-Discovery Scan" in result.stdout
    assert "Current Active Path" in result.stdout


def test_path_set_and_reset(tmp_path: Path):
    test_dir = tmp_path / "custom_mapi_data"
    test_dir.mkdir()

    try:
        set_res = runner.invoke(app, ["path", "set", str(test_dir)])
        assert set_res.exit_code == 0
        assert "MAPI path successfully configured!" in set_res.stdout

        show_res = runner.invoke(app, ["path", "show"])
        assert show_res.exit_code == 0
        assert test_dir.name in show_res.stdout
    finally:
        reset_res = runner.invoke(app, ["path", "reset"])
        assert reset_res.exit_code == 0
        assert "Custom path configuration removed" in reset_res.stdout
