from __future__ import annotations

import time
from pathlib import Path

import msgspec

from mapi_cli.paths import MAPI_EXT_ZST
from mapi_cli.tools.converter import normalize_spec
from mapi_cli.tools.extractor import extract_service_data
from mapi_cli.tools.models import CompileConfig, CompileMetrics, SpecSourceConfig
from mapi_cli.tools.utils import compress_zstd


def process_service(
    source_cfg: SpecSourceConfig,
    raw_spec_path: Path,
    data_dir: Path,
    config: CompileConfig = CompileConfig(),
) -> CompileMetrics:
    """Compile a single raw OpenAPI specification into compressed ServiceData."""
    provider = source_cfg.provider
    api = source_cfg.api
    source = source_cfg.source

    try:
        t_parse = time.perf_counter()
        spec_dict = normalize_spec(path=raw_spec_path)
        parse_dur = time.perf_counter() - t_parse

        t_extract = time.perf_counter()
        service_data = extract_service_data(f"{provider}/{api}/{source}", spec_dict)
        extract_dur = time.perf_counter() - t_extract

        # Serialize & compress
        encoded_json = msgspec.json.encode(service_data)
        compressed = compress_zstd(encoded_json, level=config.zstd_level)

        out_service_dir = data_dir / provider / source / api
        out_service_dir.mkdir(parents=True, exist_ok=True)

        target_file = out_service_dir / f"{api}{MAPI_EXT_ZST}"
        target_file.write_bytes(compressed)

        return CompileMetrics(
            provider=provider,
            api=api,
            source=source,
            status="success",
            operation_count=len(service_data.operations),
            reusable_param_count=len(service_data.components.parameters),
            parse_duration=parse_dur,
            extract_duration=extract_dur,
            mapi_path=str(target_file),
            utilize_path=str(target_file),
        )
    except Exception as e:
        return CompileMetrics(
            provider=provider,
            api=api,
            source=source,
            status="failure",
            error_message=str(e),
        )
