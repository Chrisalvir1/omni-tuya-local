"""Regression coverage for LAN entity discovery and product-specific IDs."""
import tests
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from custom_components.omni_tuya_local.cloud import _product_schema
from custom_components.omni_tuya_local.device import OmniTuyaDevice
from custom_components.omni_tuya_local.dps import schema_from_dps, dps_label
from custom_components.omni_tuya_local.light import _light_dps, OmniTuyaLight
from custom_components.omni_tuya_local.models import TuyaDeviceConfig, sanitize_device_config
from custom_components.omni_tuya_local.sensor import async_setup_entry as setup_sensors, OmniTuyaSensor
from custom_components.omni_tuya_local.switch import _switch_dps
from custom_components.omni_tuya_local import async_cleanup_device_entities


class LocalDiscoveryAudit(unittest.IsolatedAsyncioTestCase):
    def coordinator(self, config, raw):
        coord = MagicMock()
        coord.data = {"dps": {"dev": raw}}
        coord.devices = {}
        coord.store.all.return_value = {"dev": config}
        coord.get_device_config.return_value = config
        coord.dps_value.side_effect = lambda dev, key: raw.get(str(key))
        coord.entry.entry_id = "entry"
        return coord

    def test_preserves_modern_and_internal_dps_without_granting_writes(self):
        config = {"device_id": "dev", "domain": "light"}
        values = {"20": True, "21": "white", "22": 500, "23": 600, "24": "000003e803e8", "101": False}
        schema = schema_from_dps(config, values)
        self.assertEqual(set(schema), set(values))
        self.assertEqual(schema["22"]["kind"], "number")
        config["discovered_dps"] = schema
        self.assertEqual(_light_dps(config, self.coordinator(config, values)), [("20", None)])

    def test_noncontiguous_switch_ids_come_from_schema(self):
        config = {"device_id": "dev", "domain": "switch", "name": "Interruptor doble", "tuya_functions": [
            {"dp_id": 101, "code": "switch_1"}, {"dp_id": 105, "code": "switch_2"},
            {"dp_id": 16, "code": "switch_backlight"},
        ]}
        self.assertEqual([dp for dp, _ in _switch_dps(config, self.coordinator(config, {"101": True, "105": False}))], ["101", "105"])

    def test_manual_mapping_can_select_high_id(self):
        config = {"device_id": "dev", "domain": "switch", "dps_map": {
            "101": {"platform": "switch", "name": "Relé"},
            "102": {"platform": "sensor", "name": "Temperatura", "unit": "°C"},
        }}
        self.assertEqual(_switch_dps(config, self.coordinator(config, {})), [("101", "Relé")])

    def test_nested_specifications_keep_read_only_telemetry(self):
        schema = _product_schema({"success": True, "result": {"functions": [
            {"dp_id": 20, "code": "switch_led"}], "status": [
            {"dp_id": 20, "code": "switch_led"},
            {"dp_id": 42, "code": "cur_power", "values": '{"scale":2}'},
        ]}})
        by_code = {item["code"]: item for item in schema}
        self.assertFalse(by_code["switch_led"]["read_only"])
        self.assertTrue(by_code["cur_power"]["read_only"])
        self.assertEqual(by_code["cur_power"]["dp_id"], 42)

    async def test_product_sensors_exist_before_first_lan_read_with_unknown_state(self):
        config = {"device_id": "dev", "domain": "switch", "tuya_functions": [
            {"dp_id": 42, "code": "cur_power", "type": "Integer", "read_only": True, "values": '{"scale":2}'},
            {"dp_id": 43, "code": "humidity_value", "type": "Integer", "read_only": True},
        ]}
        coord = self.coordinator(config, {})
        entities = []
        await setup_sensors(SimpleNamespace(data={"omni_tuya_local": {"entry": coord}}), SimpleNamespace(entry_id="entry"), entities.extend)
        self.assertEqual({e.dps_id for e in entities}, {"42", "43"})
        self.assertTrue(all(e.native_value is None for e in entities))

    async def test_cloud_refresh_rebuilds_already_linked_entries(self):
        from custom_components.omni_tuya_local import async_reload_linked_entries
        entries = [SimpleNamespace(entry_id="a", data={"device_id": "dev"}), SimpleNamespace(entry_id="b", data={"device_id": "other"})]
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=Mock(return_value=entries), async_reload=AsyncMock(return_value=True)))
        await async_reload_linked_entries(hass, {"dev"})
        hass.config_entries.async_reload.assert_awaited_once_with("a")

    def test_corrected_primary_dp_keeps_entity_id_for_homekit(self):
        from custom_components.omni_tuya_local import async_migrate_primary_entity_ids
        config = {"device_id": "dev", "domain": "light", "tuya_functions": [{"dp_id": 20, "code": "switch_led", "type": "Boolean"}]}
        coord = self.coordinator(config, {"20": True})
        registry = Mock()
        registry.async_get_entity_id.side_effect = ["light.sala", None]
        registry.async_get.return_value = SimpleNamespace(config_entry_id="entry")
        with patch("custom_components.omni_tuya_local.er.async_get", return_value=registry):
            async_migrate_primary_entity_ids(Mock(), coord)
        registry.async_update_entity.assert_called_once_with("light.sala", new_unique_id="omni_tuya_local_dev_20")

    def test_outlet_exposes_native_device_class_homekit_uses(self):
        from custom_components.omni_tuya_local.switch import OmniTuyaSwitch
        from homeassistant.components.switch import SwitchDeviceClass
        config = {"device_id": "dev", "domain": "switch", "device_type": "outlet"}
        entity = OmniTuyaSwitch(self.coordinator(config, {"1": True}), config)
        self.assertEqual(entity.device_class, SwitchDeviceClass.OUTLET)

    def test_contact_primary_uses_product_id_not_arbitrary_fallback(self):
        from custom_components.omni_tuya_local.binary_sensor import OmniTuyaBinarySensor
        config = {"device_id": "dev", "domain": "binary_sensor", "tuya_functions": [{"dp_id": 105, "code": "doorcontact_state"}]}
        entity = OmniTuyaBinarySensor(self.coordinator(config, {"1": False, "105": True}), config)
        self.assertEqual(entity.dps_id, "105")
        self.assertTrue(entity.is_on)

    async def test_discovery_fallback_requests_product_ids(self):
        config = {"device_id": "dev", "host": "192.0.2.1", "tuya_functions": [{"dp_id": 101, "code": "switch_1", "type": "Boolean"}]}
        device = OmniTuyaDevice(Mock(), config)
        device._tuya = Mock()
        device._tuya.status.return_value = {"dps": {}}
        device._tuya.updatedps.return_value = {"dps": {"101": True}}
        self.assertEqual(device._sync_status(), {"101": True})
        device._tuya.updatedps.assert_called_once_with([101])

    def test_names_do_not_reclassify_known_actuators(self):
        for config in (
            {"name": "Luz puerta", "category": "dj", "domain": "light"},
            {"name": "Puerta garaje", "domain": "cover", "device_type": "garage_door"},
            {"name": "Puerta", "domain": "switch", "device_type": "switch"},
        ):
            self.assertEqual(sanitize_device_config(config), (config, False))

    def test_gateway_host_is_sufficient(self):
        config = TuyaDeviceConfig.from_dict({"device_id": "child", "node_id": "node", "gateway_id": "gateway", "gateway_host": "192.0.2.2"})
        self.assertTrue(config.has_host)

    def test_wired_presence_is_not_treated_as_sleeping(self):
        device = OmniTuyaDevice(Mock(), {"device_id": "dev", "domain": "binary_sensor", "device_type": "presence_sensor", "category": "ldcg"})
        self.assertFalse(device.is_sleep_device)

    def test_modern_rgb_features_and_command_use_actual_ids(self):
        config = {"device_id": "dev", "domain": "light"}
        raw = {"20": True, "21": "colour", "22": 500, "23": 500, "24": "000003e803e8"}
        coord = self.coordinator(config, raw)
        light = OmniTuyaLight(coord, config, "20")
        self.assertEqual(light._brightness_dps, "22")
        self.assertEqual(light._hsv_dps, "24")
        self.assertEqual(light._color_temp_dps, "23")
        self.assertEqual(light._mode_dps, "21")
        self.assertIsNotNone(light.hs_color)

    def test_boolean_channel_two_is_not_brightness(self):
        config = {"device_id": "dev", "domain": "light"}
        light = OmniTuyaLight(self.coordinator(config, {"1": True, "2": False}), config)
        self.assertIsNone(light._brightness_dps)

    async def test_switch_domain_keeps_zero_power_and_observed_telemetry(self):
        config = {"device_id": "dev", "domain": "switch", "device_type": "outlet", "discovered_dps": {"19": {"kind": "number"}, "9": {"kind": "number"}}}
        coord = self.coordinator(config, {"1": True, "19": 0, "9": 30})
        entities = []
        await setup_sensors(SimpleNamespace(data={"omni_tuya_local": {"entry": coord}}), SimpleNamespace(entry_id="entry"), entities.extend)
        self.assertEqual({e.dps_id for e in entities}, {"19", "9"})

    def test_schema_scaling_overrides_magnitude_guess(self):
        config = {"device_id": "dev", "domain": "switch", "device_type": "outlet", "tuya_functions": [{"dp_id": 19, "code": "cur_power", "values": '{"scale":2}'}]}
        sensor = OmniTuyaSensor(self.coordinator(config, {"19": 1234}), config, "19", {"code": "cur_power"})
        self.assertEqual(sensor.native_value, 12.34)

    async def test_cloud_import_joins_nested_functions_with_numeric_status_specifications(self):
        from custom_components.omni_tuya_local.cloud import async_fetch_cloud_devices
        async def executor(fn, *args):
            return fn(*args)
        cloud = Mock()
        cloud.getdevices.return_value = [{"id": "dev", "local_key": "test-key", "category": "cz"}]
        cloud.getfunctions.return_value = {"success": True, "result": {"functions": [{"code": "switch_1", "type": "Boolean"}]}}
        cloud.getdps.return_value = {"success": True, "result": {"functions": [{"code": "switch_1", "dp_id": 101, "type": "Boolean"}], "status": [{"code": "cur_power", "dp_id": 42, "type": "Integer", "values": '{"scale":2,"unit":"W"}'}]}}
        with patch("tinytuya.Cloud", return_value=cloud):
            devices = await async_fetch_cloud_devices(SimpleNamespace(async_add_executor_job=executor), "key", "secret", "us")
        schema = {item["code"]: item for item in devices[0]["tuya_functions"]}
        self.assertEqual(schema["switch_1"]["dp_id"], 101)
        self.assertTrue(schema["cur_power"]["read_only"])

    def test_enum_battery_is_text_not_invalid_numeric_percentage(self):
        config = {"device_id": "dev", "domain": "sensor"}
        sensor = OmniTuyaSensor(self.coordinator(config, {"3": "high"}), config, "3", {"name": "Battery state", "type": "Enum"})
        self.assertIsNone(sensor._attr_device_class)
        self.assertEqual(sensor.native_value, "high")

    def test_unknown_product_dp19_has_neutral_label(self):
        self.assertEqual(dps_label({"domain": "sensor", "category": "wsdcg"}, "19"), "DPS 19")

    async def test_cleanup_preserves_helpers_foreign_entries_and_sensors(self):
        config = {"device_id": "dev", "domain": "switch", "device_type": "switch"}
        coord = self.coordinator(config, {})
        uid = "omni_tuya_local_dev"
        entries = [
            SimpleNamespace(entity_id="light.helper", platform="switch_as_x", config_entry_id="helper", domain="light", unique_id=uid),
            SimpleNamespace(entity_id="light.foreign", platform="omni_tuya_local", config_entry_id="other", domain="light", unique_id=uid),
            SimpleNamespace(entity_id="sensor.power", platform="omni_tuya_local", config_entry_id="entry", domain="sensor", unique_id=uid+"_19"),
            SimpleNamespace(entity_id="light.old", platform="omni_tuya_local", config_entry_id="entry", domain="light", unique_id=uid),
        ]
        registry = SimpleNamespace(entities={e.entity_id: e for e in entries}, async_remove=Mock())
        with patch("custom_components.omni_tuya_local.er.async_get", return_value=registry):
            await async_cleanup_device_entities(SimpleNamespace(data={}), coord)
        registry.async_remove.assert_called_once_with("light.old")

    async def test_empty_or_error_state_does_not_mark_device_online(self):
        async def executor(fn, *args):
            return fn(*args)
        device = OmniTuyaDevice(SimpleNamespace(async_add_executor_job=executor), {"device_id": "dev", "host": "192.0.2.1"})
        client = Mock()
        client.status.return_value = {"dps": {}}
        client.updatedps.return_value = {"Err": "904"}
        with patch.object(device, "_build_tuya", return_value=client):
            await device.async_status()
        self.assertFalse(device.available)
        self.assertEqual(device.last_status_at, 0)

    def test_nonfinite_dps_are_not_persisted(self):
        self.assertEqual(schema_from_dps({}, {"1": float("nan"), "2": float("inf")}), {})
