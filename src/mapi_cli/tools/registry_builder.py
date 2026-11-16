from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import msgspec
import yaml
from mapi.models.registry import ApiInfo, MetadataFile, ServiceRegistry

log = logging.getLogger(__name__)


class RegistryBuilder:
    """Builds services.json from disk metadata files across provider directories."""

    def __init__(self, data_dir: Path, registry_path: Path) -> None:
        self.data_dir = data_dir
        self.registry_path = registry_path

    def build_registry(self) -> ServiceRegistry:
        providers: dict[str, dict[str, ApiInfo]] = {}

        if not self.data_dir.exists():
            log.warning("Data directory %s not found. Returning empty registry.", self.data_dir)
            return ServiceRegistry(version="2.0", generated_at="", providers={})

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

                        if provider_name not in providers:
                            providers[provider_name] = {}

                        if api_name not in providers[provider_name]:
                            providers[provider_name][api_name] = ApiInfo(
                                sources=[source_name],
                                operation_count=metadata.operation_count,
                                popularity_rank=metadata.popularity_rank,
                                auth_types=metadata.auth_types,
                                primary_auth=metadata.primary_auth,
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

    def save_registry(self, registry: ServiceRegistry) -> None:
        if not registry.providers:
            log.warning("Service registry is empty. Nothing to save.")
            return

        log.info("Writing service registry to %s...", self.registry_path)
        builtins_data = msgspec.to_builtins(registry)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(builtins_data, f, indent=2)
            f.write("\n")
