import tests
import unittest

from custom_components.omni_tuya_local.dps import (
    dps_kind,
    dps_label,
    discovered_dps,
    schema_from_dps,
)


class TestDps(unittest.TestCase):
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
