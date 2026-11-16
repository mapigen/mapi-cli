from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_mapi_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure tests run with an isolated config directory and never touch real user config."""
    fake_config_dir = tmp_path / "mapi_test_config"
    fake_config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("mapi_cli.config.get_config_dir", lambda: fake_config_dir)
