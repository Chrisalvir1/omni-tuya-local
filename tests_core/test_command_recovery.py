"""Check command errors and lifecycle through the real Core 2026.10 APIs."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import homeassistant.core
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from custom_components.omni_tuya_local.coordinator import OmniTuyaLocalCoordinator
from custom_components.omni_tuya_local.registry import device_for_entry
from custom_components.omni_tuya_local.switch import OmniTuyaSwitch


def test_real_ha_service_reports_rejected_off_instead_of_success(tmp_path):
    async def exercise():
        hass = HomeAssistant(str(tmp_path))
        dev = SimpleNamespace(async_set_status=AsyncMock(return_value=False))
        coord = SimpleNamespace(hass=hass, data={}, devices={"plug-1": dev}, _ensure_devices=AsyncMock(), _publish_device_state=Mock(), _schedule_command_verification=Mock(), get_device_config=Mock(return_value={"device_id": "plug-1", "domain": "switch"}))
        coord.async_set_status = lambda *args: OmniTuyaLocalCoordinator.async_set_status(coord, *args)
        entity = OmniTuyaSwitch(coord, {"device_id": "plug-1", "domain": "switch"})
        async def turn_off(call):
            await entity.async_turn_off()
        hass.services.async_register("switch", "turn_off", turn_off)
        try:
            await hass.services.async_call("switch", "turn_off", {}, blocking=True)
        except HomeAssistantError:
            pass
        else:
            raise AssertionError("HA incorrectly accepted rejected Tuya command")
        dev.async_set_status.assert_awaited_once_with(False, 1)
        await hass.async_stop()
    asyncio.run(exercise())


def test_coordinator_unload_cancels_reads_and_core_poll_timer(tmp_path):
    async def exercise():
        hass = HomeAssistant(str(tmp_path))
        entry = SimpleNamespace(entry_id="entry-1", pref_disable_polling=False, async_on_unload=Mock())
        coord = OmniTuyaLocalCoordinator(hass, entry, SimpleNamespace(all=Mock(return_value={})))
        task = asyncio.create_task(asyncio.sleep(30))
        coord._verification_tasks["plug-1"] = task
        await coord.async_shutdown()
        assert task.cancelled()
        assert coord._shutdown_requested
        assert not coord._verification_tasks
        assert coord.config_entry is entry
        await hass.async_stop()
    asyncio.run(exercise())


def test_registry_uses_core_scoped_api_signature():
    from homeassistant.helpers.device_registry import DeviceRegistry
    class OwnedRegistry:
        def __init__(self):
            self.calls = []
        def async_get_device_by_identifier(self, identifier, config_entry_id):
            self.calls.append((identifier, config_entry_id))
            return None
        def async_get_device(self, **kwargs):
            raise AssertionError("deprecated lookup used")
    registry = OwnedRegistry()
    assert device_for_entry(registry, "plug-1", "entry-1") is None
    assert registry.calls == [(("omni_tuya_local", "plug-1"), "entry-1")]
    import inspect
    assert list(inspect.signature(DeviceRegistry.async_get_device_by_identifier).parameters) == ['self', 'identifier', 'config_entry_id']
