from __future__ import annotations

import logging
from pathlib import Path

from mapi.models.domain import Parameter, ParameterRef, ServiceData
from mapi.registry.discovery import DiscoveryService, RegistryManager
from mapi.registry.loader import DiskLoader

from mapi_cli.tools.models import ValidationResult

log = logging.getLogger(__name__)


def validate_operations_and_refs(data: ServiceData, service_name: str) -> list[str]:
    """Check structural integrity and $ref consistency in ServiceData."""
    errors: list[str] = []
    operations = data.operations
    components = data.components.parameters

    if not operations:
        errors.append("No 'operations' block found.")

    for op_id, op_data in operations.items():
        if not all([op_data.service, op_data.path, op_data.method, op_data.parameters is not None]):
            errors.append(f"Operation '{op_id}' is missing required fields.")

        for param in op_data.parameters:
            if isinstance(param, ParameterRef):
                if param.component_name not in components:
                    errors.append(f"Operation '{op_id}' has a broken $ref: '{param.ref}'")
            elif isinstance(param, Parameter) and not all(
                [param.name, param.in_, param.schema_ is not None]
            ):
                errors.append(f"Inline parameter in '{op_id}' is missing required fields.")
    return errors


def validate_data_directory(data_dir: Path, registry_path: Path) -> ValidationResult:
    """Validate all services and component references in the data directory."""
    loader = DiskLoader(data_dir=data_dir, registry_path=registry_path)
    rm = RegistryManager(loader)
    discovery = DiscoveryService(rm, loader)

    try:
        providers = discovery.list_providers()
    except Exception as e:
        log.warning("No service registry found at %s: %s", registry_path, e)
        return ValidationResult(total_services=0, valid_services=0)

    total = 0
    valid = 0
    broken_refs: dict[str, list[str]] = {}
    schema_errors: dict[str, list[str]] = {}

    for provider in providers:
        for api in discovery.list_apis(provider):
            info = discovery.get_api_info(provider, api)
            for source in info.sources:
                total += 1
                service_name = f"{provider}/{api}/{source}"
                try:
                    service_data = loader.load_service(provider, api, source)
                    errs = validate_operations_and_refs(service_data, service_name)
                    if errs:
                        broken_refs[service_name] = errs
                    else:
                        valid += 1
                except Exception as e:
                    schema_errors[service_name] = [str(e)]

    return ValidationResult(
        total_services=total,
        valid_services=valid,
        broken_refs=broken_refs,
        schema_errors=schema_errors,
    )
