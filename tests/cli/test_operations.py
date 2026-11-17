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


def test_safe_markup_and_param_input_id():
    """Verify safe_markup and make_param_input_id helpers."""
    from textual.content import Content
    from textual.dom import check_identifiers

    from mapi_cli.ui.operation_view import make_param_input_id, safe_markup

    # 1. safe_markup escapes brackets so Content.from_markup parses without MarkupError
    for text in [
        "[/]",
        "files[0]",
        "[`confirm=true`]",
        "list[string]",
        "C:\\Users\\[name]",
        "Unknown command '[/]'.",
        None,
    ]:
        escaped = safe_markup(text)
        content = Content.from_markup(f"[dim]{escaped}[/]")
        assert content is not None

    # 2. make_param_input_id generates valid DOM IDs matching Textual constraints
    cases = [
        ("id", 0, "op_input_id"),
        ("user_id", 1, "op_input_user_id"),
        ("files[0]", 14, "op_input_14_files_0"),
        ("files[9]", 23, "op_input_23_files_9"),
        ("teams.any", 2, "op_input_2_teams_any"),
        ("$select", 3, "op_input_3_select"),
        ("123_invalid", 4, "op_input_4_123_invalid"),
        ("---", 5, "op_input_5_---"),
    ]
    for param_name, idx, expected in cases:
        actual = make_param_input_id(param_name, index=idx)
        assert actual == expected
        # Must pass Textual's DOM identifier check without BadIdentifier
        check_identifiers("id", actual)


async def test_operation_runner_page_with_bracket_parameters():
    """Verify OperationRunnerPage mounts and collects inputs with bracket params."""
    from textual.app import App, ComposeResult
    from textual.widgets import Input

    from mapi_cli.operations import (
        OperationAuthDetail,
        OperationParamDetail,
        OperationRequirementCheck,
    )
    from mapi_cli.ui.operation_view import OperationRunnerPage

    param_id = OperationParamDetail(
        name="id",
        in_="path",
        type_str="integer",
        is_required=True,
        description="Standard identifier",
    )
    param_bracket = OperationParamDetail(
        name="files[0]",
        in_="body",
        type_str="list[string]",
        is_required=False,
        description="File payload [`confirm=true`](https://stripe.com) or [markdown link]",
    )
    auth = OperationAuthDetail(
        is_required=True,
        is_configured=False,
        primary_auth="bearer",
        env_var_name="API_KEY",
        message="Token [test_token] required",
    )
    chk = OperationRequirementCheck(
        provider="test_prov",
        api="test_api",
        operation_id="test_op",
        method="POST",
        path="/v1/test/[id]",
        summary="Summary with [brackets]",
        description="Full desc with [markdown](link) and [0] and [/] tags",
        source="registry",
        storage_tier="Compressed",
        parameters=[param_id, param_bracket],
        required_parameters=[param_id],
        optional_parameters=[param_bracket],
        missing_parameters=[],
        auth=auth,
        can_execute=True,
        status_summary="Ready [ok]",
        example_call="/call test",
    )

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield OperationRunnerPage(chk)

    app = TestApp()
    async with app.run_test() as pilot:
        page = app.query_one(OperationRunnerPage)
        assert page is not None

        # Verify widget IDs
        id_inp = page.query_one("#op_input_id", Input)
        bracket_inp = page.query_one("#op_input_1_files_0", Input)
        assert id_inp.name == "id"
        assert bracket_inp.name == "files[0]"

        # Set values and verify collected inputs
        id_inp.value = "42"
        bracket_inp.value = "test_file.png"
        await pilot.pause()

        collected = page.get_collected_inputs()
        assert collected["id"] == 42
        assert collected["files[0]"] == "test_file.png"

        # Verify display_result and display_error with tricky strings
        page.display_result({"data": "test [brackets]"}, "call/[0]")
        page.display_error("Error: [/] failed", "call/[0]")

