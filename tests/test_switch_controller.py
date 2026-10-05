import tests
import unittest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.core import HomeAssistant
from custom_components.omni_tuya_local.const import DOMAIN
from custom_components.omni_tuya_local.switch import _switch_dps, async_setup_entry as async_setup_switch
from custom_components.omni_tuya_local.sensor import async_setup_entry as async_setup_sensor
from custom_components.omni_tuya_local import async_cleanup_device_entities


class TestSwitchController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = MagicMock()
        self.coordinator.data = {"dps": {}, "available": {}}
        self.coordinator.devices = {}
        self.coordinator.store = MagicMock()
        self.coordinator.register_entity_refresh_callback = MagicMock()

    def test_switch_dps_triple_controller(self):
        """CB03-SBL with 3 gangs and DP 16 backlight should ONLY expose channels 1, 2, 3."""
        config = {
            "device_id": "bf36e4d593706cf0f9sokk",
            "name": "Apagador Triple",
            "product_name": "CB03-SBL",
            "domain": "switch",
            "device_type": "switch",
            "discovered_dps": {
                "1": {"kind": "boolean", "name": "Boton Garaje"},
                "2": {"kind": "boolean", "name": "BOTON VENTILADOR"},
                "3": {"kind": "boolean", "name": "Luz de corredor"},
                "7": {"kind": "number", "name": "DPS 7"},
                "16": {"kind": "boolean", "name": "DPS 16"},
            },
        }
        self.coordinator.data = {
            "dps": {
                "bf36e4d593706cf0f9sokk": {
                    "1": False,
                    "2": True,
                    "3": False,
                    "7": 0,
                    "16": False,
                }
            }
        }

        channels = _switch_dps(config, self.coordinator)
        dps_ids = [c[0] for c in channels]
        self.assertEqual(dps_ids, ["1", "2", "3"])
        self.assertNotIn("16", dps_ids)
        self.assertNotIn("7", dps_ids)

        names = [c[1] for c in channels]
        self.assertEqual(names, ["Boton Garaje", "BOTON VENTILADOR", "Luz de corredor"])

    async def test_switch_setup_skips_light_domain(self):
        """A device configured as domain='light' should NOT be registered as switch entities."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_1": self.coordinator}}
        entry = MagicMock()
        entry.entry_id = "entry_1"

        config = {
            "device_id": "bf36e4d593706cf0f9sokk",
            "name": "Apagador Triple",
            "product_name": "CB03-SBL",
            "domain": "light",
            "device_type": "switch",
            "discovered_dps": {
                "1": {"kind": "boolean", "name": "DPS 1"},
                "2": {"kind": "boolean", "name": "DPS 2"},
                "3": {"kind": "boolean", "name": "DPS 3"},
            },
        }
        self.coordinator.store.all.return_value = {config["device_id"]: config}

        added_entities = []
        await async_setup_switch(hass, entry, lambda ents: added_entities.extend(ents))
        self.assertEqual(len(added_entities), 0)

    async def test_sensor_setup_excludes_switch_channels_and_internal_dps(self):
        """Sensors should NOT be created for switch buttons 1, 2, 3 or timer DP 7 on a wall switch."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_1": self.coordinator}}
        entry = MagicMock()
        entry.entry_id = "entry_1"

        config = {
            "device_id": "bf36e4d593706cf0f9sokk",
            "name": "Apagador Triple",
            "product_name": "CB03-SBL",
            "domain": "switch",
            "device_type": "switch",
            "discovered_dps": {
                "1": {"kind": "boolean", "name": "Boton Garaje"},
                "2": {"kind": "boolean", "name": "BOTON VENTILADOR"},
                "3": {"kind": "boolean", "name": "Luz de corredor"},
                "7": {"kind": "number", "name": "DPS 7"},
                "16": {"kind": "boolean", "name": "DPS 16"},
            },
        }
        self.coordinator.store.all.return_value = {config["device_id"]: config}
        self.coordinator.data = {
            "dps": {
                "bf36e4d593706cf0f9sokk": {
                    "1": False, "2": True, "3": False, "7": 0, "16": False
                }
            }
        }

        added_sensors = []
        await async_setup_sensor(hass, entry, lambda ents: added_sensors.extend(ents))
        # No phantom sensors for 1, 2, 3, 7, 16, 18, 19
        self.assertEqual(len(added_sensors), 0)

    async def test_cleanup_device_entities(self):
        """Test cleaning up duplicate light entities, phantom Canal 16, and fake sensors."""
        hass = MagicMock()
        dev_id = "bf36e4d593706cf0f9sokk"
        config = {
            "device_id": dev_id,
            "name": "Apagador Triple",
            "product_name": "CB03-SBL",
            "domain": "switch",
            "device_type": "switch",
        }
        self.coordinator.store.all.return_value = {dev_id: config}

        # Mock entity registry
        class FakeEntityEntry:
            def __init__(self, entity_id, platform, domain, unique_id):
                self.entity_id = entity_id
                self.platform = platform
                self.domain = domain
                self.unique_id = unique_id

        registry_entries = {
            f"switch.{DOMAIN}_{dev_id}": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}", DOMAIN, "switch", f"{DOMAIN}_{dev_id}"),
            f"switch.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_2", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_2"),
            f"switch.{DOMAIN}_{dev_id}_3": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_3", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_3"),
            # Duplicate / invalid entities to remove:
            f"switch.{DOMAIN}_{dev_id}_16": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_16", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_16"),
            f"light.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"light.{DOMAIN}_{dev_id}_2", DOMAIN, "light", f"{DOMAIN}_{dev_id}_2"),
            f"light.{DOMAIN}_{dev_id}_3": FakeEntityEntry(f"light.{DOMAIN}_{dev_id}_3", DOMAIN, "light", f"{DOMAIN}_{dev_id}_3"),
            f"sensor.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_2", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_2"),
            f"sensor.{DOMAIN}_{dev_id}_3": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_3", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_3"),
            f"sensor.{DOMAIN}_{dev_id}_7": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_7", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_7"),
            f"sensor.{DOMAIN}_{dev_id}_18": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_18", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_18"),
            f"sensor.{DOMAIN}_{dev_id}_19": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_19", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_19"),
        }

        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = registry_entries
        removed_ids = []
        mock_entity_registry.async_remove.side_effect = lambda eid: removed_ids.append(eid)

        from homeassistant.helpers import entity_registry as er
        er.async_get = MagicMock(return_value=mock_entity_registry)

        await async_cleanup_device_entities(hass, self.coordinator)

        # The 3 real switches must NOT be removed
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}", removed_ids)
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}_2", removed_ids)
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}_3", removed_ids)

        # All invalid / duplicate entities MUST be removed
        self.assertIn(f"switch.{DOMAIN}_{dev_id}_16", removed_ids)
        self.assertIn(f"light.{DOMAIN}_{dev_id}_2", removed_ids)
        self.assertIn(f"light.{DOMAIN}_{dev_id}_3", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_2", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_3", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_7", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_18", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_19", removed_ids)

    def test_switch_dps_double_controller(self):
        """Any 2-gang controller (Apagador Doble, CB02, TS0002) should ONLY expose channels 1 and 2."""
        config = {
            "device_id": "dev_double_123",
            "name": "Apagador Doble Pasillo",
            "product_name": "TS0002",
            "domain": "switch",
            "device_type": "switch",
            "discovered_dps": {
                "1": {"kind": "boolean", "name": "Canal 1"},
                "2": {"kind": "boolean", "name": "Canal 2"},
                "16": {"kind": "boolean", "name": "DPS 16"},
            },
        }
        self.coordinator.data = {
            "dps": {
                "dev_double_123": {
                    "1": True,
                    "2": False,
                    "16": False,
                }
            }
        }

        channels = _switch_dps(config, self.coordinator)
        dps_ids = [c[0] for c in channels]
        self.assertEqual(dps_ids, ["1", "2"])
        self.assertNotIn("16", dps_ids)

    def test_switch_dps_cloud_functions_double(self):
        """A double controller declaring cloud functions switch_1, switch_2 and switch_backlight."""
        config = {
            "device_id": "dev_cloud_2gang",
            "name": "Luz Sala",
            "domain": "switch",
            "device_type": "switch",
            "tuya_functions": [
                {"code": "switch_1", "type": "Boolean", "values": "{}", "dp_id": 1, "name": "Luz Techo"},
                {"code": "switch_2", "type": "Boolean", "values": "{}", "dp_id": 2, "name": "Luz Pared"},
                {"code": "switch_backlight", "type": "Boolean", "values": "{}", "dp_id": 16, "name": "Backlight"},
            ],
        }

        channels = _switch_dps(config, self.coordinator)
        dps_ids = [c[0] for c in channels]
        self.assertEqual(dps_ids, ["1", "2"])
        self.assertNotIn("16", dps_ids)
    async def test_cleanup_double_controller_pasillo(self):
        """Test cleaning up duplicate entities on CB02-SBL APAGADOR PASILLO."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        dev_id = "bf36979cf2634cfcbb02w4"
        config = {
            "device_id": dev_id,
            "name": "APAGADOR PASILLO",
            "product_name": "CB02-SBL",
            "domain": "switch",
            "device_type": "switch",
        }
        self.coordinator.store.all.return_value = {dev_id: config}

        class FakeEntityEntry:
            def __init__(self, entity_id, platform, domain, unique_id):
                self.entity_id = entity_id
                self.platform = platform
                self.domain = domain
                self.unique_id = unique_id

        registry_entries = {
            f"switch.{DOMAIN}_{dev_id}": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}", DOMAIN, "switch", f"{DOMAIN}_{dev_id}"),
            f"switch.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_2", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_2"),
            # Duplicate / invalid entities to remove:
            f"switch.{DOMAIN}_{dev_id}_1": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_1", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_1"),
            f"switch.{DOMAIN}_{dev_id}_16": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}_16", DOMAIN, "switch", f"{DOMAIN}_{dev_id}_16"),
            f"light.{DOMAIN}_{dev_id}": FakeEntityEntry(f"light.{DOMAIN}_{dev_id}", DOMAIN, "light", f"{DOMAIN}_{dev_id}"),
            f"light.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"light.{DOMAIN}_{dev_id}_2", DOMAIN, "light", f"{DOMAIN}_{dev_id}_2"),
            f"sensor.{DOMAIN}_{dev_id}_2": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_2", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_2"),
            f"sensor.{DOMAIN}_{dev_id}_16": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_16", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_16"),
            f"sensor.{DOMAIN}_{dev_id}_17": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_17", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_17"),
            f"sensor.{DOMAIN}_{dev_id}_19": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_19", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_19"),
        }

        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = registry_entries
        removed_ids = []
        mock_entity_registry.async_remove.side_effect = lambda eid: removed_ids.append(eid)

        from homeassistant.helpers import entity_registry as er
        er.async_get = MagicMock(return_value=mock_entity_registry)

        await async_cleanup_device_entities(hass, self.coordinator)

        # Physical channels 1 and 2 must NOT be removed
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}", removed_ids)
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}_2", removed_ids)

        # Duplicate switch for channel 1 and channel 16 must be removed
        self.assertIn(f"switch.{DOMAIN}_{dev_id}_1", removed_ids)
        self.assertIn(f"switch.{DOMAIN}_{dev_id}_16", removed_ids)

        # Ghost lights and ghost sensors must all be removed
        self.assertIn(f"light.{DOMAIN}_{dev_id}", removed_ids)
        self.assertIn(f"light.{DOMAIN}_{dev_id}_2", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_2", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_16", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_17", removed_ids)
        self.assertIn(f"sensor.{DOMAIN}_{dev_id}_19", removed_ids)

    async def test_cleanup_preserves_plug_and_sensors(self):
        """A Wifi Plug / outlet must NOT be treated as a wall switch; its power sensors must be preserved."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        dev_id = "bf2d99b46f631e0a6edjhi"
        config = {
            "device_id": dev_id,
            "name": "NEON SALA",
            "product_name": "Wifi Plug",
            "domain": "switch",
            "device_type": "outlet",
            "category": "cz",
        }
        self.coordinator.store.all.return_value = {dev_id: config}

        class FakeEntityEntry:
            def __init__(self, entity_id, platform, domain, unique_id):
                self.entity_id = entity_id
                self.platform = platform
                self.domain = domain
                self.unique_id = unique_id

        registry_entries = {
            f"switch.{DOMAIN}_{dev_id}": FakeEntityEntry(f"switch.{DOMAIN}_{dev_id}", DOMAIN, "switch", f"{DOMAIN}_{dev_id}"),
            f"sensor.{DOMAIN}_{dev_id}_17": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_17", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_17"),
            f"sensor.{DOMAIN}_{dev_id}_18": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_18", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_18"),
            f"sensor.{DOMAIN}_{dev_id}_19": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_19", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_19"),
            f"sensor.{DOMAIN}_{dev_id}_20": FakeEntityEntry(f"sensor.{DOMAIN}_{dev_id}_20", DOMAIN, "sensor", f"{DOMAIN}_{dev_id}_20"),
        }

        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = registry_entries
        removed_ids = []
        mock_entity_registry.async_remove.side_effect = lambda eid: removed_ids.append(eid)

        from homeassistant.helpers import entity_registry as er
        er.async_get = MagicMock(return_value=mock_entity_registry)

        await async_cleanup_device_entities(hass, self.coordinator)

        # Neither the switch nor the sensors should be removed
        self.assertNotIn(f"switch.{DOMAIN}_{dev_id}", removed_ids)
        self.assertNotIn(f"sensor.{DOMAIN}_{dev_id}_17", removed_ids)
        self.assertNotIn(f"sensor.{DOMAIN}_{dev_id}_18", removed_ids)
        self.assertNotIn(f"sensor.{DOMAIN}_{dev_id}_19", removed_ids)
        self.assertNotIn(f"sensor.{DOMAIN}_{dev_id}_20", removed_ids)

    async def test_device_optimistic_command(self):
        """async_set_status must update internal DPS optimistically upon success."""
        from custom_components.omni_tuya_local.device import OmniTuyaDevice

        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value={"success": True})

        cfg = {
            "device_id": "bf2d99b46f631e0a6edjhi",
            "host": "192.168.110.11",
            "local_key": "0123456789abcdef",
            "domain": "switch",
        }
        dev = OmniTuyaDevice(hass, cfg)
        self.assertIsNone(dev.dps.get("1"))

        success = await dev.async_set_status(True, 1)
        self.assertTrue(success)
        self.assertTrue(dev.dps.get("1"))
        self.assertTrue(dev.available)


if __name__ == "__main__":
    unittest.main()


