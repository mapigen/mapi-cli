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


def resolve_service_query(
    discovery: Any,
    service: str,
    api_or_query: str | None = None,
    query: str | None = None,
) -> tuple[str, str | None, str | None]:
    """Resolve service, API, and search filter query from flexible positional arguments.

    Handles:
        - ("discord", None, None) -> ("discord", "REST", None) [if 1 API]
        - ("discord/REST", None, None) -> ("discord", "REST", None)
        - ("discord/REST", "post", None) -> ("discord", "REST", "post")
        - ("discord", "REST", None) -> ("discord", "REST", None)
        - ("discord", "REST", "post") -> ("discord", "REST", "post")
        - ("discord", "post", None) -> ("discord", "REST", "post") [if 1 API]
    """
    if "/" in service:
        parts = service.strip("/").split("/")
        prov_name = resolve_provider_name(discovery, parts[0])
        resolved_api = resolve_api_name(discovery, prov_name, parts[1])
        filter_q = api_or_query or query
        return prov_name, resolved_api, filter_q

    prov_name = resolve_provider_name(discovery, service)
    if not discovery.provider_exists(prov_name):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"Provider '{service}' not found.")

    apis = discovery.list_apis(prov_name)

    if api_or_query is not None:
        matched_api = None
        for a in apis:
            if a.lower() == api_or_query.lower():
                matched_api = a
                break

        if matched_api is not None:
            return prov_name, matched_api, query

        if len(apis) == 1:
            combined_q = api_or_query if query is None else f"{api_or_query} {query}"
            return prov_name, apis[0], combined_q

        from mapi.exceptions import ServiceNotFoundError

        avail = ", ".join(apis)
        raise ServiceNotFoundError(
            f"API '{api_or_query}' not found for provider '{prov_name}'. Available APIs: {avail}"
        )

    if len(apis) == 1:
        return prov_name, apis[0], query
    elif len(apis) == 0:
        return prov_name, None, query
    else:
        return prov_name, None, query
