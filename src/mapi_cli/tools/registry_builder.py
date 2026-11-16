from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import msgspec
import yaml
from mapi.models.registry import ApiInfo, MetadataFile, ServiceRegistry

log = logging.getLogger(__name__)


class RegistryBuilder:
    """Builds mapi-registry.json from disk metadata files across provider directories."""

    def __init__(self, data_dir: Path, registry_path: Path) -> None:
        self.data_dir = data_dir
        self.registry_path = registry_path

    def build_registry(self) -> ServiceRegistry:
        providers: dict[str, dict[str, ApiInfo]] = {}

        if not self.data_dir.exists():
            log.warning("Data directory %s not found. Returning empty registry.", self.data_dir)
            return ServiceRegistry(version="2.0", generated_at="", providers={})

        overrides: dict[str, Any] = {}
        popularity: dict[str, int] = {}
        reg_dir = Path(__file__).resolve().parent.parent.parent.parent / "registry"
        overrides_path = reg_dir / "overrides.json"
        if overrides_path.exists():
            with contextlib.suppress(Exception):
                overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
        pop_path = reg_dir / "popularity.json"
        if pop_path.exists():
            with contextlib.suppress(Exception):
                popularity = json.loads(pop_path.read_text(encoding="utf-8"))

        for provider_dir in self.data_dir.iterdir():
            if not provider_dir.is_dir() or provider_dir.name.startswith("."):
                continue
            provider_name = provider_dir.name

            for source_dir in provider_dir.iterdir():
                if not source_dir.is_dir():
                    continue
                source_name = source_dir.name

                for api_dir in source_dir.iterdir():
                    if not api_dir.is_dir():
                        continue
                    api_name = api_dir.name

                    metadata_path = api_dir / "metadata.yml"
                    if not metadata_path.exists():
                        metadata_path = api_dir / "metadata.yaml"
                    if not metadata_path.exists():
                        continue

                    try:
                        raw_dict = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
                        metadata = msgspec.convert(raw_dict, type=MetadataFile)

                        auth_types = list(metadata.auth_types)
                        primary_auth = metadata.primary_auth
                        if provider_name in overrides and "auth" in overrides[provider_name]:
                            auth_override = overrides[provider_name]["auth"]
                            if "auth_types" in auth_override:
                                auth_types = auth_override["auth_types"]
                            if "primary_auth" in auth_override:
                                primary_auth = auth_override["primary_auth"]

                        pop_rank = popularity.get(provider_name, metadata.popularity_rank)

                        if provider_name not in providers:
                            providers[provider_name] = {}

                        if api_name not in providers[provider_name]:
                            providers[provider_name][api_name] = ApiInfo(
                                sources=[source_name],
                                operation_count=metadata.operation_count,
                                popularity_rank=pop_rank,
                                auth_types=auth_types,
                                primary_auth=primary_auth,
                                spec_url=getattr(metadata, "spec_url", None) or getattr(metadata, "api_reference", None),
                            )
                        else:
                            existing = providers[provider_name][api_name]
                            if source_name not in existing.sources:
                                existing.sources.append(source_name)

                    except Exception as e:
                        log.warning(
                            "Skipping %s/%s/%s: %s", provider_name, source_name, api_name, e
                        )

        return ServiceRegistry(
            version="2.0",
            generated_at=datetime.now(UTC).isoformat(),
            providers=providers,
        )

    def save_registry(self, registry: ServiceRegistry, force: bool = False) -> None:
        if not registry.providers:
            log.warning("Service registry is empty. Nothing to save.")
            return

        final_providers = dict(registry.providers)
        if self.registry_path.exists() and not force:
            try:
                existing = msgspec.json.decode(self.registry_path.read_bytes(), type=ServiceRegistry)
                for prov, apis in existing.providers.items():
                    if prov not in final_providers:
                        final_providers[prov] = dict(apis)
                    else:
                        for a_name, a_info in apis.items():
                            if a_name not in final_providers[prov]:
                                final_providers[prov][a_name] = a_info
            except Exception as e:
                log.warning("Could not merge existing registry at %s: %s", self.registry_path, e)

        merged = ServiceRegistry(
            version=registry.version,
            generated_at=datetime.now(UTC).isoformat(),
            providers=final_providers,
        )

        log.info("Writing service registry to %s...", self.registry_path)
        builtins_data = msgspec.to_builtins(merged)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.registry_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(builtins_data, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.registry_path)
