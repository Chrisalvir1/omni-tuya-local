import tests
import unittest

from custom_components.omni_tuya_local.util import (
    ha_to_tuya_brightness,
    tuya_to_ha_brightness,
    parse_physical_id,
    slugify,
)
from custom_components.omni_tuya_local.const import (
    TUYA_BRIGHTNESS_MAX,
    TUYA_BRIGHTNESS_MIN,
)


class TestUtil(unittest.TestCase):
    def test_brightness_conversions(self):
        # Minimum
        self.assertEqual(tuya_to_ha_brightness(TUYA_BRIGHTNESS_MIN), 0)
        self.assertEqual(ha_to_tuya_brightness(0), TUYA_BRIGHTNESS_MIN)

        # Maximum
        self.assertEqual(tuya_to_ha_brightness(TUYA_BRIGHTNESS_MAX), 255)
        self.assertEqual(ha_to_tuya_brightness(255), TUYA_BRIGHTNESS_MAX)

        # Mid-range
        mid_tuya = (TUYA_BRIGHTNESS_MAX + TUYA_BRIGHTNESS_MIN) // 2
        ha_val = tuya_to_ha_brightness(mid_tuya)
        self.assertTrue(120 <= ha_val <= 135)

    def test_parse_physical_id(self):
        self.assertEqual(parse_physical_id("device123"), ("device123", 1))
        self.assertEqual(parse_physical_id("device123_2"), ("device123", 2))
        self.assertEqual(parse_physical_id("device123_invalid"), ("device123_invalid", 1))

    def test_slugify(self):
        self.assertEqual(slugify("Living Room Lamp"), "living_room_lamp")
        self.assertEqual(slugify("Test-123_Device!"), "test_123_device")

    def test_max_gangs_for_device(self):
        from custom_components.omni_tuya_local.util import max_gangs_for_device

        # CB03 / Apagador Triple
        self.assertEqual(max_gangs_for_device({"product_name": "CB03-SBL"}), 3)
        self.assertEqual(max_gangs_for_device({"name": "Apagador Triple"}), 3)
        self.assertEqual(max_gangs_for_device({"name": "Switch 3 Gang"}), 3)
        self.assertEqual(max_gangs_for_device({"name": "Interruptor 3 vías"}), 3)
        self.assertEqual(max_gangs_for_device({"name": "Apagador 3 botones"}), 3)

        # Other models
        self.assertEqual(max_gangs_for_device({"product_name": "CB01"}), 1)
        self.assertEqual(max_gangs_for_device({"product_name": "CB02-SBL"}), 2)
        self.assertEqual(max_gangs_for_device({"product_name": "CB04"}), 4)
        self.assertEqual(max_gangs_for_device({"name": "Apagador Doble"}), 2)
        self.assertEqual(max_gangs_for_device({"name": "Interruptor Simple"}), 1)
        self.assertEqual(max_gangs_for_device({"name": "Switch Cuádruple"}), 4)
        self.assertEqual(max_gangs_for_device({"product_name": "WS-102"}), 2)
        self.assertEqual(max_gangs_for_device({"product_name": "4CH Smart Relay"}), 4)

        # Default fallback
        self.assertEqual(max_gangs_for_device({}), 8)


if __name__ == "__main__":
    unittest.main()

