import unittest
from copy import deepcopy
from dataclasses import replace

from thinq_demo.fixtures import number_range
from thinq_demo.profiles import inspect_profile, validate_value
from thinq_demo.service import MockCatalog


class ProfileTests(unittest.TestCase):
    def capability(self, definition):
        return inspect_profile({"property": {"group": {"field": definition}}})[0][0]

    def test_read_only(self):
        cap = self.capability({"type": "number", "mode": ["r"]})
        self.assertTrue(cap.readable)
        with self.assertRaises(ValueError):
            validate_value(cap, 12)

    def test_range_and_decimal_step(self):
        cap = self.capability(number_range(18, 30, 0.5))
        for value in (18, 24.5, 30):
            validate_value(cap, value)
        for value in (17.5, 30.5, 24.2, True, "24", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_value(cap, value)

    def test_enum_types(self):
        cap = self.capability({"type": "enum", "mode": ["w"], "value": {"w": [1, "ON"]}})
        validate_value(cap, 1)
        validate_value(cap, "ON")
        for value in (True, 1.0, "OFF"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_value(cap, value)

    def test_boolean(self):
        cap = self.capability({"type": "boolean", "mode": ["w"], "value": {"w": [True]}})
        validate_value(cap, True)
        for value in (False, 1, "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_value(cap, value)

    def test_missing_modes_never_grant_write(self):
        cap = self.capability({"type": "enum", "value": {"w": ["ON"]}})
        self.assertFalse(cap.actionable)

    def test_invalid_constraints_blocked(self):
        cases = [
            {"type": "enum", "mode": ["w"]},
            {"type": "range", "mode": ["w"], "value": {"w": {"min": 1, "max": 2, "step": 0}}},
            {"type": "range", "mode": ["w"], "value": {"w": {"min": 2, "max": 1, "step": 1}}},
            {"type": "vendorObject", "mode": ["w"]},
            {"type": "boolean", "mode": ["w"]},
            {"type": "enum", "mode": "rw", "value": {"w": ["ON"]}},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertFalse(self.capability(case).actionable)

    def test_oven_locations_units_not_merged(self):
        catalog = MockCatalog()
        caps, _ = inspect_profile(catalog.get_profile("mock-oven"))
        temperatures = [c for c in caps if c.kind == "range"]
        self.assertEqual(len(temperatures), 2)
        self.assertNotEqual(temperatures[0].key, temperatures[1].key)
        self.assertEqual(temperatures[0].context[0]["location"]["locationName"], "UPPER")
        self.assertEqual(temperatures[1].context[0]["location"]["locationName"], "LOWER")
        self.assertEqual(temperatures[0].context[1]["unit"], "C")

    def test_raw_profile_preserved(self):
        profile = MockCatalog().get_profile("mock-oven")
        before = deepcopy(profile)
        inspect_profile(profile)
        self.assertEqual(profile, before)

    def test_unknown_root_reports_warning(self):
        caps, warnings = inspect_profile({"newFormat": {"x": 1}})
        self.assertEqual(caps, [])
        self.assertTrue(warnings)

    def test_pointer_escaping(self):
        caps, _ = inspect_profile({"property": {"a/b~": number_range(0, 1)}})
        self.assertEqual(caps[0].key, "/property/a~1b~0")

    def test_extension_property_supported(self):
        caps, _ = inspect_profile({"extensionProperty": {"x": number_range(0, 1)}})
        self.assertTrue(caps[0].actionable)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = MockCatalog()
        self.key = "/property/temperature/targetTemperature"

    def test_multiple_device_types(self):
        types = {d["deviceType"] for d in self.catalog.list_devices()}
        self.assertGreaterEqual(len(types), 6)

    def test_prepare_does_not_mutate_state(self):
        before = self.catalog.get_state("mock-ac")
        self.catalog.prepare("mock-ac", self.key, 24)
        self.assertEqual(before, self.catalog.get_state("mock-ac"))

    def test_simulate_then_reject_stale_intent(self):
        intent = self.catalog.prepare("mock-ac", self.key, 24)
        result = self.catalog.simulate(intent)
        self.assertFalse(result["real_device_command_sent"])
        self.assertEqual(self.catalog.get_state("mock-ac")[self.key], 24)
        with self.assertRaises(ValueError):
            self.catalog.simulate(intent)

    def test_revalidate_tampered_intent(self):
        intent = self.catalog.prepare("mock-ac", self.key, 24)
        with self.assertRaises(ValueError):
            self.catalog.simulate(replace(intent, value=99))

    def test_offline_rejected(self):
        with self.assertRaises(ValueError):
            self.catalog.prepare("mock-offline", "/property/operation/mode", "ON")

    def test_unknown_device_and_property(self):
        for device_id, key in (("not-found", self.key), ("mock-ac", "/fake")):
            with self.subTest(device_id=device_id), self.assertRaises(ValueError):
                self.catalog.prepare(device_id, key, 24)

    def test_copy_does_not_modify_catalog(self):
        state = self.catalog.get_state("mock-ac")
        state[self.key] = 100
        self.assertEqual(self.catalog.get_state("mock-ac")[self.key], 25)


if __name__ == "__main__":
    unittest.main()
