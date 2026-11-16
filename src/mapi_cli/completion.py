from __future__ import annotations

import click

from mapi_cli.context import CliContext


def _get_context(ctx: click.Context) -> CliContext | None:
    if hasattr(ctx, "obj") and isinstance(ctx.obj, CliContext):
        return ctx.obj
    return None


def complete_provider(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Dynamic shell autocompletion for API providers."""
    c_ctx = _get_context(ctx)
    if not c_ctx:
        return []
    try:
        providers = c_ctx.client.discovery.list_providers()
        return [p for p in providers if p.startswith(incomplete)]
    except Exception:
        return []


def complete_api(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Dynamic shell autocompletion for APIs within a selected provider."""
    c_ctx = _get_context(ctx)
    if not c_ctx:
        return []
    provider = ctx.params.get("provider")
    if not provider:
        return []
    try:
        apis = c_ctx.client.discovery.list_apis(provider)
        return [a for a in apis if a.startswith(incomplete)]
    except Exception:
        return []


def complete_operation(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Dynamic shell autocompletion for operations within provider/api."""
    c_ctx = _get_context(ctx)
    if not c_ctx:
        return []
    provider = ctx.params.get("provider")
    api = ctx.params.get("api")
    if not provider or not api:
        return []
    try:
        ops = c_ctx.client.discovery.list_operations(provider, api)
        return [o for o in ops if o.startswith(incomplete)]
    except Exception:
        return []
