from __future__ import annotations

from typing import Any


def resolve_provider_name(discovery: Any, provider: str) -> str:
    """Resolve provider name case-insensitively against discovery registry.

    Allows user inputs like 'PokeAPI' to resolve to 'pokeapi'.
    """
    try:
        if discovery.provider_exists(provider):
            return provider
        for p in discovery.list_providers():
            if p.lower() == provider.lower():
                return p
    except Exception:
        pass
    return provider


def resolve_api_name(discovery: Any, provider: str, api: str) -> str:
    """Resolve API name case-insensitively against discovery registry.

    Allows user inputs like 'rest' to resolve to 'REST'.
    """
    try:
        if discovery.api_exists(provider, api):
            return api
        for a in discovery.list_apis(provider):
            if a.lower() == api.lower():
                return a
    except Exception:
        pass
    return api


def resolve_provider_and_api(discovery: Any, provider: str, api: str) -> tuple[str, str]:
    """Resolve both provider and API names case-insensitively."""
    prov = resolve_provider_name(discovery, provider)
    resolved_api = resolve_api_name(discovery, prov, api)
    return prov, resolved_api
