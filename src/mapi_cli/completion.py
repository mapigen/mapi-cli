from __future__ import annotations

from typing import Any

import click

from mapi_cli.context import CliContext
from mapi_cli.paths import resolve_data_dir


def _get_discovery(ctx: click.Context) -> Any:
    """Retrieve DiscoveryService from CliContext or create a lightweight fallback instance."""
    if hasattr(ctx, "obj") and isinstance(ctx.obj, CliContext) and ctx.obj._client:
        return ctx.obj.client.discovery

    try:
        from mapi import Mapi

        target_dir, _ = resolve_data_dir()
        client = Mapi(data_dir=target_dir)
        return client.discovery
    except Exception:
        return None


def complete_provider(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[str | tuple[str, str]]:
    """Dynamic shell autocompletion for API providers with shell descriptions."""
    discovery = _get_discovery(ctx)
    if not discovery:
        return []
    try:
        providers = discovery.list_providers()
        results: list[str | tuple[str, str]] = []
        for p in providers:
            if p.startswith(incomplete):
                results.append((p, f"Provider: {p}"))
        return results
    except Exception:
        return []


def complete_api(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[str | tuple[str, str]]:
    """Dynamic shell autocompletion for APIs within a selected provider."""
    discovery = _get_discovery(ctx)
    if not discovery:
        return []

    provider = ctx.params.get("provider")
    if not provider and args:
        # Check if first positional arg is provider
        provider = args[0]
    if not provider:
        return []

    try:
        apis = discovery.list_apis(provider)
        return [(a, f"API for {provider}") for a in apis if a.startswith(incomplete)]
    except Exception:
        return []


def complete_operation(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[str | tuple[str, str]]:
    """Dynamic shell autocompletion for operations within provider/api."""
    discovery = _get_discovery(ctx)
    if not discovery:
        return []

    provider = ctx.params.get("provider")
    api = ctx.params.get("api")
    if not provider and len(args) >= 1:
        provider = args[0]
    if not api and len(args) >= 2:
        api = args[1]

    if not provider or not api:
        return []

    try:
        ops = discovery.list_operations(provider, api)
        results: list[str | tuple[str, str]] = []
        for o in ops:
            if o.startswith(incomplete):
                results.append((o, f"Operation: {o}"))
        return results
    except Exception:
        return []


def complete_target_or_provider(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[str | tuple[str, str]]:
    """Dynamic shell completion supporting both 'provider' and 'provider/api/operation' paths."""
    discovery = _get_discovery(ctx)
    if not discovery:
        return []

    try:
        # 1. No slash yet: complete provider names
        if "/" not in incomplete:
            providers = discovery.list_providers()
            matches: list[str | tuple[str, str]] = []
            for p in providers:
                if p.startswith(incomplete):
                    matches.append((p, f"Provider: {p}"))
            return matches

        # 2. Contains slashes: parse composite path
        parts = incomplete.split("/")
        provider = parts[0]

        # Incomplete is 'provider/' or 'provider/api_prefix'
        if len(parts) == 2:
            api_prefix = parts[1]
            apis = discovery.list_apis(provider)
            return [
                (f"{provider}/{a}/", f"API: {a}")
                for a in apis
                if a.startswith(api_prefix)
            ]

        # Incomplete is 'provider/api/' or 'provider/api/op_prefix'
        if len(parts) >= 3:
            api = parts[1]
            op_prefix = parts[2]
            ops = discovery.list_operations(provider, api)
            return [
                (f"{provider}/{api}/{o}", f"Op: {o}")
                for o in ops
                if o.startswith(op_prefix)
            ]

    except Exception:
        pass
    return []


def complete_call_parameters(
    ctx: click.Context, args: list[str], incomplete: str
) -> list[str | tuple[str, str]]:
    """Autocomplete parameter names as 'param_name=' for the target operation."""
    discovery = _get_discovery(ctx)
    if not discovery:
        return []

    provider: str | None = None
    api: str | None = None
    operation: str | None = None

    # Check positional args
    if len(args) >= 1 and "/" in args[0]:
        parts = args[0].split("/")
        if len(parts) >= 3:
            provider, api, operation = parts[0], parts[1], parts[2]
    elif len(args) >= 3:
        provider, api, operation = args[0], args[1], args[2]

    if not provider or not api or not operation:
        return []

    try:
        op = discovery.get_operation(provider, api, operation)
        from mapi.models.domain import Parameter, ParameterRef
        from mapi.registry.loader import DiskLoader

        resolved_parameters: list[Parameter] = []
        target_dir, _ = resolve_data_dir()
        loader = DiskLoader(data_dir=target_dir)

        # Attempt to load service data to resolve ParameterRef components
        sdata = None
        try:
            info = discovery.get_api_info(provider, api)
            sdata = loader.load_service(provider, api, info.sources[0])
        except Exception:
            pass

        for p in op.parameters:
            if isinstance(p, Parameter):
                resolved_parameters.append(p)
            elif isinstance(p, ParameterRef) and sdata:
                comp = sdata.components.parameters.get(p.component_name)
                if isinstance(comp, Parameter):
                    resolved_parameters.append(comp)

        results: list[str | tuple[str, str]] = []
        for p in resolved_parameters:
            param_token = f"{p.name}="
            if param_token.startswith(incomplete):
                req_str = "required" if p.required else "optional"
                desc = f"({req_str} {p.in_}) {p.description or ''}".strip()
                results.append((param_token, desc[:50]))
        return results
    except Exception:
        return []
