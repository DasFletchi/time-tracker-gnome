import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import DataStore


class DataStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp_dir.name, "data.json")
        self.store = DataStore(path=self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_json(self):
        with open(self.path, "r", encoding="utf-8") as data_file:
            return json.load(data_file)

    def test_add_seconds_creates_pretty_json_file(self):
        self.store.add_seconds("2026-08-27", 90)

        self.assertEqual(self.store.get_seconds("2026-08-27"), 90)
        self.assertEqual(self.read_json(), {"2026-08-27": 90})
        with open(self.path, "r", encoding="utf-8") as data_file:
            self.assertTrue(data_file.read().endswith("\n"))

    def test_external_manual_edit_is_preserved_before_next_tick(self):
        self.store.add_seconds("2026-08-27", 60)
        with open(self.path, "w", encoding="utf-8") as data_file:
            json.dump({"2026-08-27": 7200, "2026-08-28": 1800}, data_file)

        self.store.add_seconds("2026-08-27", 1)

        self.assertEqual(
            self.read_json(),
            {"2026-08-27": 7201, "2026-08-28": 1800},
        )

    def test_invalid_manual_edit_does_not_erase_last_valid_data(self):
        self.store.add_seconds("2026-08-27", 120)
        with open(self.path, "w", encoding="utf-8") as data_file:
            data_file.write("{not valid json")

        self.store.add_seconds("2026-08-27", 1)

        self.assertEqual(self.read_json(), {"2026-08-27": 121})

    def test_invalid_keys_and_negative_values_are_ignored(self):
        with open(self.path, "w", encoding="utf-8") as data_file:
            json.dump(
                {
                    "2026-08-27": 3600,
                    "not-a-date": 99,
                    "2026-08-28": -1,
                    "2026-08-29": True,
                },
                data_file,
            )

        reloaded_store = DataStore(path=self.path)

        self.assertEqual(reloaded_store.get_seconds("2026-08-27"), 3600)
        self.assertEqual(reloaded_store.get_seconds("2026-08-28"), 0)
        self.assertEqual(reloaded_store.get_seconds("not-a-date"), 0)


if __name__ == "__main__":
    unittest.main()
