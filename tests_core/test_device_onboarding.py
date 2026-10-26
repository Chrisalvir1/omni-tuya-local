"""One-by-one onboarding regressions exercised with real HA flow classes."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import homeassistant.core
from custom_components.omni_tuya_local.config_flow import OmniTuyaLocalConfigFlow, _test_tuya_connection


CONFIG = {"device_id": "stable", "lan_device_id": "current", "host": "192.0.2.4", "local_key": "test-key", "version": "3.3", "domain": "switch", "device_type": "outlet"}


def test_empty_cloud_sync_does_not_override_saved_region():
    from custom_components.omni_tuya_local import SYNC_CLOUD_SCHEMA
    assert "region" not in SYNC_CLOUD_SCHEMA({})
    assert SYNC_CLOUD_SCHEMA({"region": "eu"})["region"] == "eu"


def test_probe_keeps_numeric_schema_and_closes_socket():
    client = Mock()
    client.status.return_value = {"dps": {"101": True, "19": 0}}
    config = dict(CONFIG)
    with patch("tinytuya.Device", return_value=client) as constructor:
        assert _test_tuya_connection(config, "3.3")
    assert constructor.call_args.kwargs["dev_id"] == "current"
    assert set(config["discovered_dps"]) == {"101", "19"}
    client.close.assert_called_once()


def test_probe_rejects_empty_and_malformed_dps():
    for raw in ({"dps": {}}, {"dps": []}, {"dps": {"1": True}, "Err": "904"}):
        client = Mock()
        client.status.return_value = raw
        client.updatedps.return_value = raw
        with patch("tinytuya.Device", return_value=client):
            assert not _test_tuya_connection(dict(CONFIG), "3.3")
        client.close.assert_called_once()


def test_failed_tcp_probe_stays_on_local_form():
    async def exercise():
        flow = OmniTuyaLocalConfigFlow()
        flow.hass = Mock()
        flow._device_data = {}
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_step_device_details = AsyncMock()
        with patch("custom_components.omni_tuya_local.config_flow._async_test_tuya_connection", return_value=False):
            await flow.async_step_local_device(dict(CONFIG))
        flow.async_step_device_details.assert_not_awaited()
        assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "connection"}
    asyncio.run(exercise())


def test_final_individual_import_persists_corrected_lan_inventory():
    async def exercise():
        flow = OmniTuyaLocalConfigFlow()
        flow.hass = Mock()
        flow._device_data = {**CONFIG, "host": "192.0.2.99", "version": "3.5", "tuya_functions": [{"dp_id": 101, "code": "switch"}], "discovered_dps": {"101": {"kind": "boolean"}}}
        flow.async_create_entry = Mock()
        store = SimpleNamespace(async_load=AsyncMock(), add=AsyncMock())
        with patch("custom_components.omni_tuya_local.storage.TuyaDeviceStore", return_value=store):
            await flow.async_step_device_details({"name": "Enchufe nuevo"})
        saved = store.add.call_args.args[0]
        assert saved["host"] == "192.0.2.99"
        assert saved["version"] == "3.5"
        assert saved["tuya_functions"][0]["dp_id"] == 101
        assert saved["discovered_dps"]["101"]["kind"] == "boolean"
        assert flow.async_create_entry.call_args.kwargs["data"] == saved
    asyncio.run(exercise())
