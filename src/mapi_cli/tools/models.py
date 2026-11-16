from __future__ import annotations

from typing import Annotated, Literal

import msgspec
from msgspec import Meta

NonEmptyStr = Annotated[str, Meta(min_length=1)]


class SpecSourceConfig(msgspec.Struct, frozen=True, gc=False):
    """Upstream OpenAPI specification entry."""

    provider: NonEmptyStr
    api: NonEmptyStr
    source: NonEmptyStr
    url: NonEmptyStr
    popularity_rank: int = 999
    primary_auth: str = "none"
    auth_types: list[str] = msgspec.field(default_factory=list)


class FetchResult(msgspec.Struct, frozen=True, gc=False):
    """Result of downloading an upstream specification."""

    provider: str
    api: str
    source: str
    status: Literal["downloaded", "skipped", "failure"]
    bytes_downloaded: int = 0
    duration_sec: float = 0.0
    output_path: str | None = None
    error_message: str | None = None


class CompileConfig(msgspec.Struct, frozen=True, gc=False):
    """Options governing extraction and serialization."""

    format_version: int = 3
    emit_msgpack: bool = False
    emit_json: bool = True
    zstd_level: int = 3
    force: bool = False


class CompileMetrics(msgspec.Struct, frozen=True, gc=False):
    """Telemetry captured during service compilation."""

    provider: str
    api: str
    source: str
    status: Literal["success", "failure", "skipped"]
    operation_count: int = 0
    reusable_param_count: int = 0
    parse_duration: float = 0.0
    extract_duration: float = 0.0
    mapi_path: str | None = None
    utilize_path: str | None = None
    error_message: str | None = None


class ValidationResult(msgspec.Struct, frozen=True, gc=False):
    """Integrity check report for services and components."""

    total_services: int
    valid_services: int
    broken_refs: dict[str, list[str]] = msgspec.field(default_factory=dict)
    schema_errors: dict[str, list[str]] = msgspec.field(default_factory=dict)
