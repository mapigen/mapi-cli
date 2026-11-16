from __future__ import annotations

from pathlib import Path

import msgspec
from mapi.models.domain import ParameterRef, ServiceData
from mapi.models.registry import ApiInfo, ServiceRegistry
from mapi.registry.loader import DiskLoader

from mapi_cli.tools.extractor import extract_service_data
from mapi_cli.tools.utils import compress_zstd


def test_cli_compiler_and_sdk_loader_contract(tmp_path: Path):
    """Verify that ServiceData produced by mapi-cli is fully compatible with mapi.DiskLoader."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Contract Test API", "version": "1.0.0"},
        "servers": [{"url": "https://api.contract.com/v1"}],
        "paths": {
            "/users/{id}": {
                "get": {
                    "operationId": "get_user",
                    "summary": "Get user",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                }
            }
        },
    }

    # 1. Compile ServiceData using mapi_cli extractor
    sdata = extract_service_data("contract_svc", spec)
    assert isinstance(sdata, ServiceData)
    assert "get_user" in sdata.operations

    # 2. Write to disk
    service_dir = tmp_path / "data" / "contract" / "openapi" / "REST"
    service_dir.mkdir(parents=True)
    payload = msgspec.json.encode(sdata)
    compressed = compress_zstd(payload)
    (service_dir / "REST.mapi.json.zst").write_bytes(compressed)
    (service_dir / "REST.utilize.json.zst").write_bytes(compressed)

    # Write registry
    reg = ServiceRegistry(
        version="2.0",
        generated_at="2026-11-16T12:00:00Z",
        providers={
            "contract": {
                "REST": ApiInfo(
                    sources=["openapi"],
                    operation_count=1,
                    popularity_rank=1,
                    auth_types=[],
                    primary_auth="none",
                )
            }
        },
    )
    reg_file = tmp_path / "mapi-registry.json"
    reg_file.write_bytes(msgspec.json.encode(reg))

    # 3. Read using SDK DiskLoader
    loader = DiskLoader(data_dir=tmp_path / "data", registry_path=reg_file)
    loaded_sdata = loader.load_service("contract", "REST", "openapi")

    assert loaded_sdata.service_name == "contract_svc"
    assert "get_user" in loaded_sdata.operations
    loaded_op = loaded_sdata.operations["get_user"]
    assert loaded_op.path == "/users/{id}"
    assert loaded_op.method == "GET"
    assert len(loaded_op.parameters) == 1
    assert isinstance(loaded_op.parameters[0], ParameterRef)

    # Check component parameter resolution
    fp = loaded_op.parameters[0].component_name
    param = loaded_sdata.components.parameters[fp]
    assert param.name == "id"
    assert param.in_ == "path"
    assert param.required is True
