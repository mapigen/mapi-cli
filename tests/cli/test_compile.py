from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mapi_cli.app import app
from mapi_cli.paths import PRIMARY_REGISTRY_FILENAME

runner = CliRunner()


def test_compile_root_command(tmp_path: Path):
    """Test 'mapi compile' directly at root generates mapi-registry.json."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_file = tmp_path / PRIMARY_REGISTRY_FILENAME

    result = runner.invoke(app, ["compile", "-d", str(data_dir), "-o", str(out_file)])
    assert result.exit_code == 0
    assert "Registry compiled" in result.stdout
    assert PRIMARY_REGISTRY_FILENAME in result.stdout


def test_build_alias_command(tmp_path: Path):
    """Test 'mapi build' alias."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_file = tmp_path / PRIMARY_REGISTRY_FILENAME

    result = runner.invoke(app, ["build", "-d", str(data_dir), "-o", str(out_file)])
    assert result.exit_code == 0
    assert "Registry compiled" in result.stdout


def test_tools_registry_build_backward_compatibility(tmp_path: Path):
    """Test legacy 'mapi tools registry-build' command."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_file = tmp_path / PRIMARY_REGISTRY_FILENAME

    result = runner.invoke(app, ["tools", "registry-build", "-d", str(data_dir), "-o", str(out_file)])
    assert result.exit_code == 0
    assert "Registry compiled" in result.stdout
