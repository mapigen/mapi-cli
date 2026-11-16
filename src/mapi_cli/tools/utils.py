from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import msgspec
import yaml
import zstandard as zstd
from mapi.models import Parameter

log = logging.getLogger(__name__)

VALID_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def decompress_zstd(compressed: bytes) -> bytes:
    """Decompress zstandard data."""
    return zstd.ZstdDecompressor().decompress(compressed)


def compress_zstd(data: bytes, level: int = 4) -> bytes:
    """Compress data with zstandard."""
    return zstd.ZstdCompressor(level=level).compress(data)


def load_spec(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON spec from the given path, handling .zst compression."""
    try:
        if path.name.endswith(".zst"):
            compressed_content = path.read_bytes()
            decompressed_content = decompress_zstd(compressed_content)
            return msgspec.json.decode(decompressed_content)

        content = path.read_text(encoding="utf-8")
        if path.suffix in (".yml", ".yaml"):
            return yaml.safe_load(content)
        elif path.suffix == ".json":
            return msgspec.json.decode(content)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
    except Exception as e:
        log.error("Failed to load spec file %s: %s", path, e)
        raise


def count_openapi_operations(spec: dict[str, Any]) -> int:
    """Count the number of operations in a raw OpenAPI spec."""
    count = 0
    for path_item in spec.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method_name, operation_details in path_item.items():
            if (
                method_name.lower() in VALID_METHODS
                and isinstance(operation_details, dict)
                and operation_details.get("operationId")
            ):
                count += 1
    return count


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a $ref pointer in the OpenAPI spec."""
    parts = ref.strip("#/").split("/")
    node: Any = spec
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            log.warning("Could not resolve $ref: '%s'. Part '%s' not found.", ref, part)
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _get_raw_parameter_details(param: dict[str, Any]) -> dict[str, Any]:
    return param.copy()


def _get_canonical_parameter(
    param: dict[str, Any], operation_required: list[str]
) -> Parameter | None:
    param_name = param.get("name", "")
    if not param_name:
        log.warning("Skipping parameter with no name: %s", param)
        return None
    is_required = param_name in operation_required or param.get("required", False)
    return Parameter(
        name=param_name,
        in_=param.get("in", "query"),
        description=param.get("description", ""),
        required=is_required,
        schema_=param.get("schema", {}),
    )


def _unwrap_schema_properties(
    schema: dict[str, Any], spec: dict[str, Any], visited: set[str]
) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    if "$ref" in schema:
        ref_path = schema["$ref"]
        if ref_path in visited:
            return []
        visited.add(ref_path)
        resolved = _resolve_ref(spec, ref_path)
        return _unwrap_schema_properties(resolved, spec, visited)

    if "allOf" in schema:
        for sub_schema in schema["allOf"]:
            if isinstance(sub_schema, dict):
                params.extend(_unwrap_schema_properties(sub_schema, spec, visited))

    for name, prop_data in schema.get("properties", {}).items():
        if not isinstance(prop_data, dict):
            continue
        if "$ref" in prop_data:
            ref_path = prop_data["$ref"]
            if ref_path in visited:
                continue
            visited.add(ref_path)
            param_details = {"name": name, "in": "body", "type": "object"}
            param_details.update(_get_raw_parameter_details(prop_data))
            params.append(param_details)
        else:
            param_details = {"name": name, "in": "body"}
            param_details.update(_get_raw_parameter_details(prop_data))
            params.append(param_details)

    return params


def get_params_from_operation(
    op_details: dict[str, Any], path_params: list[dict[str, Any]], spec: dict[str, Any]
) -> list[Parameter]:
    params: list[Parameter] = []
    required_params = op_details.get("required", [])

    for param_def in path_params + op_details.get("parameters", []):
        if not isinstance(param_def, dict):
            continue
        if "$ref" in param_def:
            param_def = _resolve_ref(spec, param_def["$ref"])
        if "name" in param_def and "in" in param_def:
            canonical_param = _get_canonical_parameter(param_def, required_params)
            if canonical_param:
                params.append(canonical_param)

    request_body = op_details.get("requestBody", {})
    if "$ref" in request_body:
        request_body = _resolve_ref(spec, request_body["$ref"])

    content = request_body.get("content", {})
    if isinstance(content, dict):
        for media_type in content.values():
            if isinstance(media_type, dict) and "schema" in media_type:
                is_required = request_body.get("required", False)
                unwrapped_params = _unwrap_schema_properties(media_type["schema"], spec, set())
                for param in unwrapped_params:
                    if is_required:
                        param["required"] = True
                    canonical_param = _get_canonical_parameter(
                        param, required_params if is_required else []
                    )
                    if canonical_param:
                        params.append(canonical_param)

    return params


def extract_auth_info(spec: dict[str, Any]) -> dict[str, Any]:
    auth_types: list[str] = []
    primary_auth: str = "none"

    security_schemes: dict[str, Any] = spec.get("components", {}).get("securitySchemes", {})
    if isinstance(security_schemes, dict):
        for scheme_details in security_schemes.values():
            if not isinstance(scheme_details, dict):
                continue
            auth_type = scheme_details.get("type")
            if auth_type == "http":
                scheme = scheme_details.get("scheme", "").lower()
                if scheme == "bearer":
                    auth_types.append("bearer_token")
                elif scheme == "basic":
                    auth_types.append("basic_auth")
            elif auth_type == "apiKey":
                auth_types.append("api_key")
            elif auth_type == "oauth2":
                auth_types.append("oauth2")

    if auth_types:
        primary_auth = auth_types[0]

    return {"auth_types": auth_types, "primary_auth": primary_auth}
