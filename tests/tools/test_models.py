from __future__ import annotations

import msgspec

from mapi_cli.tools.models import (
    SpecSourceConfig,
    ValidationResult,
)


def test_spec_source_config():
    cfg = SpecSourceConfig(
        provider="test",
        api="REST",
        source="openapi",
        url="https://api.example.com/spec.json",
    )
    encoded = msgspec.json.encode(cfg)
    decoded = msgspec.json.decode(encoded, type=SpecSourceConfig)
    assert decoded.provider == "test"
    assert decoded.popularity_rank == 999


def test_validation_result():
    vr = ValidationResult(total_services=10, valid_services=10)
    assert vr.broken_refs == {}
    assert vr.schema_errors == {}
