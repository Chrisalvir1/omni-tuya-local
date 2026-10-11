import tests
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.omni_tuya_local.dps import (
    dps_kind,
    dps_label,
    discovered_dps,
    schema_from_dps,
)


class TestDps(unittest.TestCase):
    def test_numeric_dps_read_does_not_alias_cloud_status_code(self):
        from custom_components.omni_tuya_local.coordinator import OmniTuyaLocalCoordinator

        coordinator = object.__new__(OmniTuyaLocalCoordinator)
        coordinator.data = {"dps": {"door-1": {"code:battery_percentage": 75}}, "available": {}}
        coordinator.devices = {}
        coordinator.store = MagicMock()
        coordinator.store.get.return_value = None

        self.assertIsNone(coordinator.dps_value("door-1", "2"))

    def test_cloud_status_codes_do_not_inflate_switch_channel_count(self):
        from custom_components.omni_tuya_local.util import max_gangs_for_device

        config = {
            "device_type": "switch",
            "category": "kg",
            "initial_dps": {"code:switch_1": True, "code:switch_2": False},
        }
        self.assertEqual(max_gangs_for_device(config), 1)

    def test_door_schema_is_not_synthesized_from_category(self):
        from custom_components.omni_tuya_local.models import sanitize_device_config

        config, _ = sanitize_device_config({"name": "Door", "category": "mcs"})
        with patch("custom_components.omni_tuya_local.util.max_gangs_for_device", return_value=4):
            self.assertEqual(discovered_dps(config), {})

    def test_numeric_battery_entity_does_not_consume_unmapped_cloud_code(self):
        from custom_components.omni_tuya_local.sensor import OmniTuyaSensor

        coordinator = MagicMock()
        coordinator.is_available.return_value = True
        coordinator.dps_value.return_value = None
        config = {
            "device_id": "door-1",
            "name": "Door",
            "initial_dps": {"code:battery_percentage": 75},
        }
        sensor = OmniTuyaSensor(coordinator, config, "2", {"code": "battery_percentage"})
        self.assertIsNone(sensor.native_value)

    def test_diagnostics_aggregates_scoped_config_entries_without_secrets(self):
        from custom_components.omni_tuya_local import _async_register_services
        from custom_components.omni_tuya_local.coordinator import OmniTuyaLocalCoordinator
        class Store:
            def __init__(self, device_id):
                self.device_id = device_id

            def all(self):
                return {self.device_id: {"device_id": self.device_id}}

            def get(self, device_id):
                return {
                    "device_id": device_id,
                    "name": device_id,
                    "local_key": "must-not-leak",
                    "host": "192.0.2.1",
                } if device_id == self.device_id else None

        class Coordinator(OmniTuyaLocalCoordinator):
            def __init__(self, device_id):
                self.store = Store(device_id)
                self.devices = {}
                self.data = {"dps": {}, "available": {}}

            def is_available(self, device_id):
                return False

            def dps_value(self, device_id):
                return None

        class Services:
            registered = False

            def has_service(self, domain, name):
                return self.registered

            def async_register(self, domain, name, handler, **kwargs):
                self.registered = True
                if domain == "omni_tuya_local" and name == "diagnostics":
                    self.handler = handler

        services = Services()
        hass = SimpleNamespace(
            data={"omni_tuya_local": {"entry-a": Coordinator("dev-a"), "entry-b": Coordinator("dev-b")}},
            services=services,
        )
        _async_register_services(hass, "entry-a")

        async def run():
            return await services.handler(None)

        result = __import__("asyncio").run(run())
        self.assertEqual(result["total_devices"], 2)
        self.assertEqual({item["device_id"] for item in result["devices"]}, {"dev-a", "dev-b"})
        self.assertNotIn("local_key", result["devices"][0])

    def test_contact_product_dps_names_remain_neutral_without_schema(self):
        config = {"device_type": "door_sensor", "category": "mcs"}
        for dp_id in ("1", "2", "3", "4"):
            self.assertEqual(dps_label(config, dp_id), f"DPS {dp_id}")

    def test_dps_kind(self):
        self.assertEqual(dps_kind(True), "boolean")
        self.assertEqual(dps_kind(False), "boolean")
        self.assertEqual(dps_kind(42), "number")
        self.assertEqual(dps_kind(3.14), "number")
        self.assertEqual(dps_kind("standby"), "text")
        self.assertIsNone(dps_kind({"nested": "dict"}))
        self.assertIsNone(dps_kind([1, 2, 3]))

    def test_dps_label_predefined_profiles(self):
        # Vacuum
        vacuum_cfg = {"domain": "vacuum", "category": "sd"}
        self.assertEqual(dps_label(vacuum_cfg, "2"), "Inicio de limpieza")
        self.assertEqual(dps_label(vacuum_cfg, "3"), "Modo de limpieza")
        self.assertEqual(dps_label(vacuum_cfg, "6"), "Batería")

        # Outlet
        outlet_cfg = {"domain": "switch", "device_type": "outlet"}
        self.assertEqual(dps_label(outlet_cfg, "1"), "Toma 1")
        self.assertEqual(dps_label(outlet_cfg, "19"), "Potencia")
        self.assertEqual(dps_label(outlet_cfg, "20"), "Voltaje")

        # Light
        light_cfg = {"domain": "light", "device_type": "light"}
        self.assertEqual(dps_label(light_cfg, "1"), "Luz 1")
        self.assertEqual(dps_label(light_cfg, "2"), "Luz 2")

        # Switch
        switch_cfg = {"domain": "switch", "device_type": "switch"}
        self.assertEqual(dps_label(switch_cfg, "1"), "Canal 1")
        self.assertEqual(dps_label(switch_cfg, "2"), "Canal 2")
        self.assertEqual(dps_label(switch_cfg, "17"), "Energía")
        self.assertEqual(dps_label(switch_cfg, "18"), "Corriente")
        self.assertEqual(dps_label(switch_cfg, "19"), "Potencia")
        self.assertEqual(dps_label(switch_cfg, "20"), "Voltaje")

        # Fallback
        generic_cfg = {"domain": "switch", "device_type": "generic"}
        self.assertEqual(dps_label(generic_cfg, "99"), "DPS 99")

    def test_discovered_dps_and_schema_from_dps(self):
        config = {
            "domain": "switch",
            "device_type": "outlet",
            "discovered_dps": {
                "1": {"kind": "boolean", "name": "Toma 1"},
                "19": {"kind": "number", "name": "Potencia"},
            }
        }
        disc = discovered_dps(config)
        self.assertIn("1", disc)
        self.assertEqual(disc["1"]["kind"], "boolean")
        self.assertIn("19", disc)
        self.assertEqual(disc["19"]["kind"], "number")

        live_values = {"1": True, "19": 150, "20": 120}
        schema = schema_from_dps(config, live_values)
        self.assertIn("20", schema)
        self.assertEqual(schema["20"]["kind"], "number")
        self.assertEqual(schema["20"]["name"], "Voltaje")


if __name__ == "__main__":
    unittest.main()
