"""Regressions for rejected writes, DHCP recovery and executor socket races."""
import tests
import asyncio
import threading
import unittest
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.exceptions import HomeAssistantError
from custom_components.omni_tuya_local.device import OmniTuyaDevice
from custom_components.omni_tuya_local.coordinator import OmniTuyaLocalCoordinator
from custom_components.omni_tuya_local.registry import device_for_entry
from custom_components.omni_tuya_local.switch import OmniTuyaSwitch

CONFIG = {"device_id": "plug-1", "host": "192.0.2.10", "local_key": "test-key", "domain": "switch"}


class CommandRegressions(unittest.IsolatedAsyncioTestCase):
    def make_device(self):
        loop = asyncio.get_running_loop()
        hass = SimpleNamespace(async_add_executor_job=lambda func, *args: loop.run_in_executor(None, partial(func, *args)))
        device = OmniTuyaDevice(hass, CONFIG)
        device._tuya = Mock()
        device._last_dps = {"1": True}
        return device

    async def test_removed_device_closes_lan_listener_and_client(self):
        close = Mock()
        hass = SimpleNamespace(async_add_executor_job=AsyncMock(side_effect=lambda fn, *args: fn(*args)))
        coordinator = SimpleNamespace(hass=hass, devices={"plug-1": SimpleNamespace(close=close)})
        await OmniTuyaLocalCoordinator._async_discard_device(coordinator, "plug-1")
        close.assert_called_once_with()
        self.assertNotIn("plug-1", coordinator.devices)

    async def test_rejection_keeps_actual_state_and_never_repeats_payload(self):
        dev = self.make_device()
        client = dev._tuya
        client.set_status.return_value = {"Err": "904", "Error": "unexpected", "Payload": "private-payload"}
        self.assertFalse(await dev.async_set_status(False))
        self.assertTrue(dev.dps["1"])
        client.set_value.assert_not_called()
        self.assertIn("904", dev.last_error_detail)
        self.assertNotIn("private-payload", dev.last_error_detail)

    async def test_null_ack_remains_compatible_with_tinytuya(self):
        dev = self.make_device()
        dev._tuya.set_status.return_value = None  # TinyTuya's valid empty ACK.
        self.assertTrue(await dev.async_set_status(False))
        self.assertFalse(dev.dps["1"])

    async def test_status_and_command_share_one_io_channel(self):
        dev = self.make_device()
        entered, release, polled = threading.Event(), threading.Event(), threading.Event()
        def write(*args, **kwargs):
            entered.set()
            release.wait(1)
            return {"dps": {"1": False}}
        def read():
            polled.set()
            return {"dps": {"1": False}}
        dev._tuya.set_status.side_effect = write
        dev._tuya.status.side_effect = read
        command = asyncio.create_task(dev.async_set_status(False))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 1))
            poll = asyncio.create_task(dev.async_status())
            await asyncio.sleep(0.02)
            self.assertFalse(polled.is_set(), "poll touched command's socket")
            release.set()
            self.assertTrue(await command)
            await poll
            self.assertTrue(polled.is_set())
        finally:
            release.set()
            await command

    async def test_timeout_does_not_claim_success_or_allow_late_worker_overlap(self):
        dev = self.make_device()
        client = dev._tuya
        entered, release, polled = threading.Event(), threading.Event(), threading.Event()
        def write(*args, **kwargs):
            entered.set()
            release.wait(1)
            return None
        client.set_status.side_effect = write
        client.status.side_effect = lambda: (polled.set() or {"dps": {"1": False}})
        with patch.object(dev, '_build_tuya', return_value=client), patch('custom_components.omni_tuya_local.device._COMMAND_TIMEOUT', 0.03):
            try:
                self.assertFalse(await dev.async_set_status(False))
                self.assertTrue(entered.is_set())
                self.assertTrue(dev.dps["1"])
                self.assertFalse(dev.available)
                poll = asyncio.create_task(dev.async_status())
                await asyncio.sleep(0.02)
                self.assertFalse(polled.is_set(), "cancelled executor worker still owns socket")
                release.set()
                await poll
                self.assertFalse(dev.dps["1"])
                self.assertTrue(dev.available)
            finally:
                release.set()

    async def test_reported_state_has_priority_over_the_command_request(self):
        dev = self.make_device()
        dev._tuya.set_status.return_value = {"dps": {"1": True}}
        self.assertTrue(await dev.async_set_status(False))
        self.assertTrue(dev.dps["1"])

    async def test_named_state_does_not_claim_numeric_dps_without_product_mapping(self):
        dev = self.make_device()
        dev._tuya.set_status.return_value = None
        await dev.async_set_status(False)
        dev._tuya.status.return_value = {"dps": {"switch": True}}
        await dev.async_status()
        self.assertFalse(dev.dps["1"])
        self.assertTrue(dev.dps["switch"])

    async def test_protocol_recovery_uses_verified_reads_and_closes_candidate(self):
        dev = self.make_device()
        bad = dev._tuya
        bad.status.return_value = bad.updatedps.return_value = {'Err': '904', 'Error': 'Unexpected Payload'}
        candidate = Mock()
        candidate.status.return_value = {'dps': {'1': True}}
        def build(version=None):
            return candidate if version == '3.4' else bad
        with patch.object(dev, '_build_tuya', side_effect=build):
            self.assertTrue((await dev.async_status())['1'])
        self.assertEqual(dev.detected_protocol_version, '3.4')
        self.assertEqual(dev.config.local_key, 'test-key')
        candidate.set_status.assert_not_called()
        candidate.set_value.assert_not_called()
        candidate.close.assert_called_once()

    async def test_protocol_recovery_includes_tiny_tuya_v32(self):
        dev = self.make_device()
        candidate = Mock()
        candidate.status.return_value = {"dps": {"1": True}}

        def build(version=None):
            return candidate if version == "3.2" else dev._tuya

        with patch.object(dev, "_build_tuya", side_effect=build):
            result = await dev._async_probe_protocol_versions()
        self.assertEqual(result, ("3.2", {"1": True}))
        candidate.close.assert_called_once()

    async def test_value_and_multiple_value_rejections_do_not_mutate_state(self):
        for method, args in (("async_set_value", (1, False)), ("async_set_values", ({"1": False},))):
            with self.subTest(method=method):
                dev = self.make_device()
                dev._tuya.set_value.return_value = dev._tuya.set_multiple_values.return_value = {"Err": "914", "Error": "bad key"}
                self.assertFalse(await getattr(dev, method)(*args))
                self.assertTrue(dev.dps["1"])

    async def test_services_propagate_failure_for_every_command_shape(self):
        dev = SimpleNamespace(async_set_status=AsyncMock(return_value=False), async_set_value=AsyncMock(return_value=False), async_set_values=AsyncMock(return_value=False))
        coord = SimpleNamespace(_ensure_devices=AsyncMock(), devices={"plug-1": dev}, _publish_device_state=Mock(), _schedule_command_verification=Mock())
        for method, args in (("async_set_status", (False,)), ("async_set_value", (1, False)), ("async_set_values", ({"1": False},))):
            with self.subTest(method=method):
                with self.assertRaises(HomeAssistantError):
                    await getattr(OmniTuyaLocalCoordinator, method)(coord, "plug-1", *args)
        self.assertEqual(coord._schedule_command_verification.call_count, 3)

    async def test_dhcp_update_persists_entry_and_reloads_without_name_error(self):
        entry = SimpleNamespace(data={"device_id": "plug-1", "host": "192.0.2.10"})
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=Mock(return_value=[entry]), async_update_entry=Mock()))
        coord = SimpleNamespace(hass=hass, store=SimpleNamespace(add=AsyncMock()), entry=SimpleNamespace(entry_id="entry-1"), async_reload_devices=AsyncMock())
        registry = SimpleNamespace(async_get_device_by_identifier=Mock(return_value=None))
        with patch('homeassistant.helpers.device_registry.async_get', return_value=registry):
            await OmniTuyaLocalCoordinator._async_update_device(coord, {**CONFIG, "host": "192.0.2.11"})
        self.assertEqual(hass.config_entries.async_update_entry.call_args.kwargs['data']['host'], "192.0.2.11")
        self.assertEqual(hass.config_entries.async_update_entry.call_args.kwargs['data']['device_id'], "plug-1")
        coord.async_reload_devices.assert_awaited_once()
        registry.async_get_device_by_identifier.assert_called_once_with(("omni_tuya_local", "plug-1"), "entry-1")

    async def test_batch_poll_cannot_restore_state_captured_before_a_new_command(self):
        ready, finish = asyncio.Event(), asyncio.Event()
        fast = SimpleNamespace(dps={"1": True}, available=True, is_sleep_device=False, detected_protocol_version=None, consecutive_failures=0)
        slow = SimpleNamespace(dps={"1": False}, available=True, is_sleep_device=False, detected_protocol_version=None, consecutive_failures=0)
        async def fast_poll():
            ready.set()
            return {"1": True}
        async def slow_poll():
            await finish.wait()
            return {"1": False}
        fast.async_status, slow.async_status = fast_poll, slow_poll
        store = SimpleNamespace(get=Mock(return_value={"discovered_dps": {}}), all=Mock(return_value={}))
        coord = SimpleNamespace(_ensure_devices=AsyncMock(), devices={"fast": fast, "slow": slow}, store=store, _adjust_poll_interval=Mock(), _schedule_lan_recovery_if_needed=Mock(), _notify_entity_refresh=Mock())
        with patch('custom_components.omni_tuya_local.coordinator.schema_from_dps', return_value={}):
            poll = asyncio.create_task(OmniTuyaLocalCoordinator._async_update_data(coord))
            await ready.wait()
            fast.dps = {"1": False}  # A write ACK arrived while the other poll was pending.
            finish.set()
            result = await poll
        self.assertFalse(result['dps']['fast']['1'])

    async def test_plain_udp_presence_does_not_claim_working_lan_control(self):
        dev = self.make_device()
        dev._consecutive_failures = 4
        cfg = {**CONFIG, 'version': '3.3'}
        coord = SimpleNamespace(store=SimpleNamespace(get=Mock(return_value=cfg)), devices={'plug-1': dev})
        OmniTuyaLocalCoordinator._handle_discovered_device(coord, 'plug-1', cfg['host'], '3.3')
        self.assertFalse(dev.available)
        self.assertEqual(dev.consecutive_failures, 4)

    async def test_value_timeouts_do_not_claim_success(self):
        for method, sync_method, args in (("async_set_value", "_sync_set_value", (1, False)), ("async_set_values", "_sync_set_values", ({"1": False},))):
            with self.subTest(method=method):
                dev = self.make_device()
                with patch.object(dev, sync_method, side_effect=TimeoutError()):
                    self.assertFalse(await getattr(dev, method)(*args))
                self.assertTrue(dev.dps['1'])
                self.assertFalse(dev.available)

    async def test_recovery_scan_persists_changed_address_in_config_entry(self):
        old = {**CONFIG, 'ip': CONFIG['host']}
        updated = {**old, 'host': '192.0.2.11', 'ip': '192.0.2.11', 'synced': True}
        entry = SimpleNamespace(data={'device_id': 'plug-1', 'host': CONFIG['host']})
        hass = SimpleNamespace(data={'omni_tuya_local': {}}, config_entries=SimpleNamespace(async_entries=Mock(return_value=[entry]), async_update_entry=Mock()))
        inventory = SimpleNamespace(async_load=AsyncMock(), all=Mock(return_value={'plug-1': old}), get=Mock(return_value=old), add=AsyncMock())
        coord = SimpleNamespace(hass=hass, _lan_refresh_lock=asyncio.Lock())
        with patch('custom_components.omni_tuya_local.coordinator.TuyaDeviceStore', return_value=inventory), patch('custom_components.omni_tuya_local.discovery.async_scan_network', new=AsyncMock(return_value=[updated])):
            await OmniTuyaLocalCoordinator._async_recover_lan_addresses(coord)
        inventory.add.assert_awaited_once_with(updated)
        self.assertEqual(hass.config_entries.async_update_entry.call_args.kwargs['data']['host'], '192.0.2.11')

    async def test_switch_propagates_home_assistant_command_error(self):
        coord = SimpleNamespace(data={}, async_set_status=AsyncMock(side_effect=HomeAssistantError('unconfirmed')), get_device_config=Mock(return_value=CONFIG))
        entity = OmniTuyaSwitch(coord, CONFIG)
        with self.assertRaises(HomeAssistantError):
            await entity.async_turn_off()


class RegistryRegressions(unittest.TestCase):
    def test_current_registry_miss_never_uses_deprecated_unscoped_lookup(self):
        registry = SimpleNamespace(async_get_device_by_identifier=Mock(return_value=None), async_get_device=Mock())
        self.assertIsNone(device_for_entry(registry, "plug-1", "entry-1"))
        registry.async_get_device.assert_not_called()

    def test_older_core_keeps_supported_registry_lookup(self):
        found = object()
        registry = SimpleNamespace(async_get_device=Mock(return_value=found))
        self.assertIs(device_for_entry(registry, "plug-1", "entry-1"), found)

    def test_switch_known_boolean_encodings_and_unknown_values(self):
        coord = SimpleNamespace(data={}, get_device_config=Mock(return_value=CONFIG), dps_value=Mock())
        entity = OmniTuyaSwitch(coord, CONFIG)
        for raw, expected in ((True, True), (False, False), (1, True), (0, False), ('true', True), ('off', False), ('ON', True), ('invalid', None), (9, None)):
            with self.subTest(raw=raw):
                coord.dps_value.return_value = raw
                self.assertIs(entity.is_on, expected)
