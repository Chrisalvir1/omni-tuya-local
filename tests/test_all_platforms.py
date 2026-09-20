import unittest
from unittest.mock import MagicMock, patch
import sys

import tests  # initialize mocks

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

class TestAllPlatforms(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.data = {}
        self.entry = MagicMock()
        self.entry.entry_id = "test_entry"
        self.coordinator = MagicMock()
        self.coordinator.store = MagicMock()
        self.coordinator.data = {"dps": {}, "available": {}}
        self.coordinator.devices = {}
        self.coordinator.register_entity_refresh_callback = MagicMock()
        self.hass.data["omni_tuya_local"] = {"test_entry": self.coordinator}

    def test_import_and_setup_all_platforms(self):
        platforms = [
            "switch",
            "light",
            "sensor",
            "binary_sensor",
            "climate",
            "cover",
            "fan",
            "humidifier",
            "lock",
            "number",
            "select",
            "vacuum",
            "alarm_control_panel",
            "button",
            "text",
        ]

        dummy_devices = {
            "dev_switch": {
                "device_id": "dev_switch",
                "name": "Smart Switch",
                "domain": "switch",
                "device_type": "outlet",
                "category": "cz",
                "discovered_dps": {"1": {"kind": "boolean", "name": "DPS 1"}, "19": {"kind": "number", "name": "DPS 19"}},
                "tuya_functions": [{"code": "switch", "type": "Boolean", "values": "{}"}, {"code": "cur_power", "type": "Integer", "values": "{}"}],
            },
            "dev_light": {
                "device_id": "dev_light",
                "name": "Smart Light",
                "domain": "light",
                "device_type": "light",
                "category": "dj",
                "discovered_dps": {"1": {"kind": "boolean", "name": "DPS 1"}, "2": {"kind": "number", "name": "DPS 2"}},
            },
            "dev_vacuum": {
                "device_id": "dev_vacuum",
                "name": "Robot Vacuum",
                "domain": "vacuum",
                "device_type": "robot_vacuum",
                "category": "sd",
                "discovered_dps": {"2": {"kind": "boolean", "name": "DPS 2"}, "6": {"kind": "number", "name": "DPS 6"}},
            },
            "dev_climate": {
                "device_id": "dev_climate",
                "name": "Thermostat",
                "domain": "climate",
                "device_type": "climate",
                "category": "wk",
                "discovered_dps": {"1": {"kind": "boolean", "name": "DPS 1"}, "2": {"kind": "number", "name": "DPS 2"}},
            },
            "dev_fan": {
                "device_id": "dev_fan",
                "name": "Fan",
                "domain": "fan",
                "device_type": "fan",
                "category": "fs",
                "discovered_dps": {"1": {"kind": "boolean", "name": "DPS 1"}},
            },
            "dev_humidifier": {
                "device_id": "dev_humidifier",
                "name": "Humidifier",
                "domain": "humidifier",
                "device_type": "humidifier",
                "category": "jsq",
                "discovered_dps": {"1": {"kind": "boolean", "name": "DPS 1"}},
            },
        }
        self.coordinator.store.all.return_value = dummy_devices

        for p in platforms:
            mod = __import__(f"custom_components.omni_tuya_local.{p}", fromlist=["async_setup_entry"])
            self.assertTrue(hasattr(mod, "async_setup_entry"), f"Platform {p} has no async_setup_entry")
            
            entities_added = []
            def add_entities(ents):
                entities_added.extend(ents)

            import asyncio
            asyncio.run(mod.async_setup_entry(self.hass, self.entry, add_entities))
            print(f"Platform {p}: {len(entities_added)} entities added successfully")

if __name__ == "__main__":
    unittest.main()
