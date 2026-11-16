from __future__ import annotations

import click
from typer.testing import CliRunner

from mapi_cli.app import app
from mapi_cli.completion import (
    complete_call_parameters,
    complete_provider,
    complete_target_or_provider,
)

runner = CliRunner()


def test_completion_show_bash():
    result = runner.invoke(app, ["completion", "show", "bash"])
    assert result.exit_code == 0
    assert "_MAPI_COMPLETE=bash_source" in result.stdout


def test_completion_show_zsh():
    result = runner.invoke(app, ["completion", "show", "zsh"])
    assert result.exit_code == 0
    assert "_MAPI_COMPLETE=zsh_source" in result.stdout


def test_completion_show_fish():
    result = runner.invoke(app, ["completion", "show", "fish"])
    assert result.exit_code == 0
    assert "_MAPI_COMPLETE=fish_source" in result.stdout


def test_completion_default_callback():
    result = runner.invoke(app, ["completion"])
    assert result.exit_code == 0
    assert "Terminal Tab Completion" in result.stdout


def test_complete_provider_function():
    ctx = click.Context(click.Command("test"))
    matches = complete_provider(ctx, [], "poke")
    match_values = [m[0] if isinstance(m, tuple) else m for m in matches]
    assert "pokeapi" in match_values


def test_complete_target_or_provider():
    ctx = click.Context(click.Command("test"))
    # 1. Provider prefix
    prov_matches = complete_target_or_provider(ctx, [], "pok")
    prov_values = [m[0] if isinstance(m, tuple) else m for m in prov_matches]
    assert "pokeapi" in prov_values

    # 2. API prefix
    api_matches = complete_target_or_provider(ctx, [], "pokeapi/")
    api_values = [m[0] if isinstance(m, tuple) else m for m in api_matches]
    assert "pokeapi/REST/" in api_values

    # 3. Operation prefix
    op_matches = complete_target_or_provider(ctx, [], "pokeapi/REST/poke")
    op_values = [m[0] if isinstance(m, tuple) else m for m in op_matches]
    assert "pokeapi/REST/pokemon_retrieve" in op_values


def test_complete_call_parameters():
    ctx = click.Context(click.Command("test"))
    matches = complete_call_parameters(ctx, ["pokeapi/REST/pokemon_retrieve"], "i")
    match_values = [m[0] if isinstance(m, tuple) else m for m in matches]
    assert "id=" in match_values
