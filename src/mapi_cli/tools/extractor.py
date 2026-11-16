from __future__ import annotations

import hashlib
from typing import Any

import msgspec
from mapi.models.domain import (
    Components,
    Operation,
    Parameter,
    ParameterRef,
    ParameterUnion,
    Server,
    ServiceData,
)

from mapi_cli.tools.utils import VALID_METHODS, get_params_from_operation


def get_param_fingerprint(param: Parameter) -> str:
    """Create a stable SHA-256 fingerprint for a canonical Parameter."""
    encoded = msgspec.json.encode(
        {"name": param.name, "in": param.in_, "required": param.required, "schema": param.schema_}
    )
    return hashlib.sha256(encoded).hexdigest()


def extract_service_data(
    service_name: str,
    spec: dict[str, Any],
    servers: list[Server] | None = None,
) -> ServiceData:
    """Extract an OpenAPI spec directly into a strongly-typed ServiceData struct."""
    canonical_params: dict[str, Parameter] = {}
    op_param_hashes: dict[str, list[str]] = {}

    paths = spec.get("paths", {})
    if isinstance(paths, dict):
        for _path, methods_dict in paths.items():
            if not isinstance(methods_dict, dict):
                continue
            path_level_params: list[dict[str, Any]] = methods_dict.get("parameters", [])
            for method, details_dict in methods_dict.items():
                if method.lower() not in VALID_METHODS or not isinstance(details_dict, dict):
                    continue
                op_id = details_dict.get("operationId")
                if not op_id:
                    continue

                op_params = get_params_from_operation(details_dict, path_level_params, spec)
                hashes = []
                for p in op_params:
                    fp = get_param_fingerprint(p)
                    hashes.append(fp)
                    if fp not in canonical_params:
                        canonical_params[fp] = p
                op_param_hashes[op_id] = hashes

    # Servers extraction
    if servers is None:
        extracted_servers: list[Server] = []
        raw_servers = spec.get("servers", [])
        if isinstance(raw_servers, list):
            for s in raw_servers:
                if isinstance(s, dict) and "url" in s:
                    extracted_servers.append(
                        Server(
                            url=s["url"],
                            description=s.get("description", ""),
                            variables=s.get("variables", {}),
                        )
                    )
        servers = extracted_servers

    operations: dict[str, Operation] = {}
    if isinstance(paths, dict):
        for path, methods_dict in paths.items():
            if not isinstance(methods_dict, dict):
                continue
            for method, details_dict in methods_dict.items():
                if method.lower() not in VALID_METHODS or not isinstance(details_dict, dict):
                    continue
                op_id = details_dict.get("operationId")
                if not op_id:
                    continue

                final_params: list[ParameterUnion] = []
                seen: set[str] = set()
                for fp in op_param_hashes.get(op_id, []):
                    if fp in seen:
                        continue
                    seen.add(fp)
                    final_params.append(ParameterRef(ref=f"#/components/parameters/{fp}"))

                operations[op_id] = Operation(
                    service=service_name,
                    path=path,
                    method=method.upper(),
                    operation_id=op_id,
                    summary=details_dict.get("summary", ""),
                    description=details_dict.get("description", ""),
                    deprecated=details_dict.get("deprecated", False),
                    parameters=final_params,
                )

    schemas = spec.get("components", {}).get("schemas", {})

    return ServiceData(
        format_version=3,
        service_name=service_name,
        servers=servers,
        components=Components(parameters=canonical_params, schemas=schemas),
        operations=operations,
    )
