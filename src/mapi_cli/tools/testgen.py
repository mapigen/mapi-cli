from __future__ import annotations

import logging
from pathlib import Path

from mapi.models.domain import Parameter, ServiceData

log = logging.getLogger(__name__)


def generate_test_case(param: Parameter) -> str:
    """Generate mock argument for a parameter."""
    p_type = param.schema_.get("type", "string") if param.schema_ else "string"
    if p_type == "integer":
        return "1"
    if p_type == "boolean":
        return "True"
    return f"'{param.name}_val'"


def generate_service_integration_test(
    provider: str, api: str, source: str, service_data: ServiceData, output_file: Path
) -> None:
    """Generate an integration test file for a provider/api service."""
    lines = [
        "# Auto-generated integration test by mapi-cli",
        "from __future__ import annotations",
        "import pytest",
        "from mapi import Mapi, RequestConfig",
        "",
        f"@pytest.mark.parametrize('operation', {list(service_data.operations.keys())[:5]})",
        f"def test_{provider}_{api.lower()}_dry_run(operation):",
        "    client = Mapi()",
        f"    res = client.execute('{provider}', '{api}', '{source}', operation, _dry_run=True)",
        "    assert res.metadata.status == 'dry_run'",
        "    assert isinstance(res.data, RequestConfig)",
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
