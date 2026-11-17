from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from mapi_cli.paths import (
    MAPI_EXT_JSON,
    MAPI_EXT_MSGPACK,
    MAPI_EXT_MSGPACK_ZST,
    MAPI_EXT_ZST,
)
from mapi_cli.storage import ApiStorageTier, get_api_storage_tier, is_api_local


def test_storage_tier_hierarchy():
    """Verify tier priority: Cached > Compressed > Downloaded > Not Downloaded."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        provider = "testprovider"
        api = "testapi"
        source = "github"
        s_dir = data_dir / provider / source / api

        # Mock client
        client = MagicMock()
        client.discovery._resolve_source.return_value = source
        client.is_cached.return_value = False

        # 1. Tier 0: Not Downloaded
        t0 = get_api_storage_tier(client, data_dir, provider, api, source)
        assert isinstance(t0, ApiStorageTier)
        assert t0.status == "Not Downloaded"
        assert t0.is_cached is False
        assert t0.is_compressed is False
        assert t0.is_downloaded is False
        assert is_api_local(data_dir, provider, source, api, client) is False

        # 2. Tier 1: Downloaded (uncompressed .mapi.json)
        s_dir.mkdir(parents=True, exist_ok=True)
        json_file = s_dir / f"{api}{MAPI_EXT_JSON}"
        json_file.write_text("{}", encoding="utf-8")

        t1 = get_api_storage_tier(client, data_dir, provider, api, source)
        assert t1.status == "Downloaded"
        assert t1.is_cached is False
        assert t1.is_compressed is False
        assert t1.is_downloaded is True
        assert t1.format == "json"
        assert is_api_local(data_dir, provider, source, api, client) is True

        # Test uncompressed .mapi.msgpack format as well
        json_file.unlink()
        msgpack_file = s_dir / f"{api}{MAPI_EXT_MSGPACK}"
        msgpack_file.write_bytes(b"\x80")
        t1_msgpack = get_api_storage_tier(client, data_dir, provider, api, source)
        assert t1_msgpack.status == "Downloaded"
        assert t1_msgpack.format == "msgpack"

        # 3. Tier 2: Compressed (.mapi.json.zst) - higher tier than downloaded
        zst_file = s_dir / f"{api}{MAPI_EXT_ZST}"
        zst_file.write_bytes(b"\x28\xb5\x2f\xfd")

        t2 = get_api_storage_tier(client, data_dir, provider, api, source)
        assert t2.status == "Compressed"
        assert t2.is_cached is False
        assert t2.is_compressed is True
        assert t2.is_downloaded is True
        assert t2.format == "zst"

        # Test msgpack.zst format
        zst_file.unlink()
        msgpack_zst_file = s_dir / f"{api}{MAPI_EXT_MSGPACK_ZST}"
        msgpack_zst_file.write_bytes(b"\x28\xb5\x2f\xfd")
        t2_msgpack = get_api_storage_tier(client, data_dir, provider, api, source)
        assert t2_msgpack.status == "Compressed"
        assert t2_msgpack.format == "msgpack.zst"

        # 4. Tier 3: Cached (in-memory RAM cache via is_cached) - highest tier
        client.is_cached.return_value = True
        t3 = get_api_storage_tier(client, data_dir, provider, api, source)
        assert t3.status == "Cached"
        assert t3.is_cached is True
        assert t3.is_compressed is True
        assert t3.is_downloaded is True
