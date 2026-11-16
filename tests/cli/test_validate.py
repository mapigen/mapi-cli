from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mapi_cli.app import app
from mapi_cli.paths import PRIMARY_REGISTRY_FILENAME

runner = CliRunner()


def test_validate_root_command(tmp_path: Path):
    """Test 'mapi validate' directly at root."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    reg_file = tmp_path / PRIMARY_REGISTRY_FILENAME
    reg_file.write_text('{"version": "2.0", "providers": {}}', encoding="utf-8")

    result = runner.invoke(app, ["validate", "-d", str(data_dir), "-r", str(reg_file)])
    assert result.exit_code == 0
    assert "Validation Report" in result.stdout
    assert PRIMARY_REGISTRY_FILENAME in result.stdout


def test_validate_root_fallback_to_services_json(tmp_path: Path):
    """Test 'mapi validate' automatically falls back to legacy services.json."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    reg_file = tmp_path / "services.json"
    reg_file.write_text('{"version": "2.0", "providers": {}}', encoding="utf-8")

    result = runner.invoke(app, ["validate", "-d", str(data_dir)])
    assert result.exit_code == 0
    assert "Validation Report" in result.stdout


def test_tools_validate_backward_compatibility(tmp_path: Path):
    """Test legacy 'mapi tools validate' command still works."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    reg_file = tmp_path / PRIMARY_REGISTRY_FILENAME
    reg_file.write_text('{"version": "2.0", "providers": {}}', encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", "-d", str(data_dir), "-r", str(reg_file)])
    assert result.exit_code == 0
    assert "Validation Report" in result.stdout
