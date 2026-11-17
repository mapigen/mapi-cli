from __future__ import annotations

import os
from unittest.mock import patch

from mapi import Mapi
from mapi.models.request import RequestConfig

from mapi_cli.operations import (
    _parse_typed_value,
    check_operation_requirements,
    execute_operation_call,
    format_param_type,
    parse_operation_call_args,
)
from mapi_cli.paths import resolve_data_dir


def test_format_param_type():
    """Verify OpenAPI schema type formatting."""
    assert format_param_type({"type": "integer"}) == "integer"
    assert format_param_type({"type": "string", "format": "date-time"}) == "string:date-time"
    assert format_param_type({"type": "array", "items": {"type": "string"}}) == "list[string]"
    assert format_param_type({"$ref": "#/components/schemas/User"}) == "User"
    assert format_param_type(None) == "any"


def test_parse_typed_value():
    """Verify parsing string values respecting schema types."""
    assert _parse_typed_value("123", expected_type="string") == "123"
    assert _parse_typed_value("123", expected_type="integer") == 123
    assert _parse_typed_value("3.14", expected_type="number") == 3.14
    assert _parse_typed_value("true", expected_type="boolean") is True
    assert _parse_typed_value("false", expected_type="boolean") is False
    assert _parse_typed_value('{"key": "val"}') == {"key": "val"}
    assert _parse_typed_value("random_string") == "random_string"


def test_parse_operation_call_args():
    """Verify parsing key=val argument lists."""
    args = ["id=25", "limit=10", "verbose"]
    parsed = parse_operation_call_args(args)
    assert parsed["id"] == 25
    assert parsed["limit"] == 10
    assert parsed["verbose"] is True


def test_check_operation_requirements_missing_and_satisfied():
    """Verify missing argument detection and satisfaction on pokeapi."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)

    # 1. Missing required 'id'
    chk_missing = check_operation_requirements(client, "pokeapi", "REST", "ability_retrieve")
    assert chk_missing.can_execute is False
    assert len(chk_missing.missing_parameters) == 1
    assert chk_missing.missing_parameters[0].name == "id"
    assert "Missing argument(s)" in chk_missing.status_summary
    assert "/call id=<string>" in chk_missing.example_call

    # 2. Satisfied with id='1'
    chk_ok = check_operation_requirements(
        client, "pokeapi", "REST", "ability_retrieve", kwargs={"id": "1"}
    )
    assert chk_ok.can_execute is True
    assert len(chk_ok.missing_parameters) == 0
    assert "Ready to call" in chk_ok.status_summary


def test_check_operation_requirements_auth_discord():
    """Verify auth requirement inspection and environment variable check on discord."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)

    # Without token in environment
    with patch.dict(os.environ, {}, clear=True):
        chk_no_auth = check_operation_requirements(
            client, "discord", "REST", "get_my_application"
        )
        assert chk_no_auth.auth.is_required is True
        assert chk_no_auth.auth.is_configured is False
        assert chk_no_auth.auth.scheme == "Bot"
        assert chk_no_auth.can_execute is False
        assert "MAPI_DISCORD_TOKEN" in chk_no_auth.status_summary

    # With MAPI_DISCORD_TOKEN set
    with patch.dict(os.environ, {"MAPI_DISCORD_TOKEN": "mock_bot_token"}):
        chk_with_auth = check_operation_requirements(
            client, "discord", "REST", "get_my_application"
        )
        assert chk_with_auth.auth.is_configured is True
        assert chk_with_auth.can_execute is True
        assert "Ready to call" in chk_with_auth.status_summary


def test_execute_operation_call_dry_run_and_curl():
    """Verify dry-run and curl execution via RequestConfig."""
    data_dir, _ = resolve_data_dir()
    client = Mapi(data_dir=data_dir)

    chk = check_operation_requirements(
        client, "pokeapi", "REST", "ability_retrieve", kwargs={"id": "1"}
    )

    # Dry run
    dry_res = execute_operation_call(client, chk, {"id": "1"}, dry_run=True)
    assert isinstance(dry_res, RequestConfig)
    assert dry_res.method == "GET"
    assert "https://pokeapi.co/api/v2/ability/1/" in dry_res.url

    # cURL
    curl_res = execute_operation_call(client, chk, {"id": "1"}, emit_curl=True)
    assert isinstance(curl_res, RequestConfig)
    assert "curl" in curl_res.to_curl()
