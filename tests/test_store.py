import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import DataStore
import tracker as tracker_module
from tracker import SAVE_INTERVAL_SECONDS, TICK_SECONDS, TimeTracker


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

    def test_add_seconds_is_buffered_until_save(self):
        self.store.add_seconds("2026-08-27", 90)

        self.assertEqual(self.store.get_seconds("2026-08-27"), 90)
        self.assertFalse(os.path.exists(self.path))

        self.assertTrue(self.store.save())
        self.assertEqual(self.read_json(), {"2026-08-27": 90})
        with open(self.path, "r", encoding="utf-8") as data_file:
            self.assertTrue(data_file.read().endswith("\n"))

    def test_file_check_is_throttled_between_saves(self):
        self.store.add_seconds("2026-08-27", 60)
        self.store._last_external_check = time.monotonic()

        with mock.patch.object(
            self.store,
            "_get_file_signature",
            wraps=self.store._get_file_signature,
        ) as signature_check:
            self.store.add_seconds("2026-08-27", 5)

        self.assertEqual(signature_check.call_count, 0)
        self.assertEqual(self.store.get_seconds("2026-08-27"), 65)

    def test_external_manual_edit_is_preserved_before_next_save(self):
        self.store.add_seconds("2026-08-27", 60)
        self.store.save()
        with open(self.path, "w", encoding="utf-8") as data_file:
            json.dump({"2026-08-27": 7200, "2026-08-28": 1800}, data_file)

        self.store.add_seconds("2026-08-27", 1)
        self.store.save()

        self.assertEqual(
            self.read_json(),
            {"2026-08-27": 7201, "2026-08-28": 1800},
        )

    def test_pending_seconds_are_merged_with_manual_edit(self):
        self.store.add_seconds("2026-08-27", 60)
        with open(self.path, "w", encoding="utf-8") as data_file:
            json.dump({"2026-08-27": 7200}, data_file)

        self.store.save()

        self.assertEqual(self.read_json(), {"2026-08-27": 7260})

    def test_invalid_manual_edit_does_not_erase_last_valid_data(self):
        self.store.add_seconds("2026-08-27", 120)
        self.store.save()
        with open(self.path, "w", encoding="utf-8") as data_file:
            data_file.write("{not valid json")

        self.store.add_seconds("2026-08-27", 1)
        self.store.save()

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


class IdleMonitorTests(unittest.TestCase):
    def setUp(self):
        tracker_module._idle_monitor_connection = None
        self.gio = mock.Mock()
        self.gio.BusType.SESSION = object()
        self.gio.DBusCallFlags.NONE = object()
        self.glib = mock.Mock()
        self.glib.VariantType.new.return_value = object()

    def tearDown(self):
        tracker_module._idle_monitor_connection = None

    def test_idle_monitor_connection_is_reused(self):
        connection = mock.Mock()
        reply = mock.Mock()
        reply.unpack.return_value = (12_345,)
        connection.call_sync.return_value = reply
        self.gio.bus_get_sync.return_value = connection

        with mock.patch.object(tracker_module, "Gio", self.gio), mock.patch.object(
            tracker_module,
            "GLib",
            self.glib,
        ):
            self.assertEqual(tracker_module.get_idle_time_ms(), 12_345)
            self.assertEqual(tracker_module.get_idle_time_ms(), 12_345)

        self.gio.bus_get_sync.assert_called_once()
        self.assertEqual(connection.call_sync.call_count, 2)

    def test_idle_monitor_failure_returns_zero_and_resets_connection(self):
        connection = mock.Mock()
        connection.call_sync.side_effect = RuntimeError("D-Bus not available")
        self.gio.bus_get_sync.return_value = connection

        with mock.patch.object(tracker_module, "Gio", self.gio), mock.patch.object(
            tracker_module,
            "GLib",
            self.glib,
        ):
            self.assertEqual(tracker_module.get_idle_time_ms(), 0)

        self.assertIsNone(tracker_module._idle_monitor_connection)


class FakeStore:
    def __init__(self, save_result=True):
        self.save_result = save_result
        self.save_calls = 0

    def save(self):
        self.save_calls += 1
        return self.save_result


class TimeTrackerSaveIntervalTests(unittest.TestCase):
    def test_default_intervals_reduce_wakeups_and_writes(self):
        self.assertEqual(TICK_SECONDS, 5)
        self.assertEqual(SAVE_INTERVAL_SECONDS, 60)

    def setUp(self):
        self.store = FakeStore()
        self.tracker = TimeTracker(self.store, save_interval_seconds=60)
        self.tracker.last_save = 100.0

    def test_save_is_not_due_before_interval(self):
        self.tracker._save_if_due(159.9)

        self.assertEqual(self.store.save_calls, 0)
        self.assertEqual(self.tracker.last_save, 100.0)

    def test_save_occurs_once_when_interval_is_due(self):
        self.tracker._save_if_due(160.0)

        self.assertEqual(self.store.save_calls, 1)
        self.assertEqual(self.tracker.last_save, 160.0)

    def test_failed_save_is_retried_on_the_next_tick(self):
        self.store.save_result = False
        self.tracker._save_if_due(160.0)
        self.store.save_result = True
        self.tracker._save_if_due(161.0)

        self.assertEqual(self.store.save_calls, 2)
        self.assertEqual(self.tracker.last_save, 161.0)

    def test_stop_flushes_pending_data(self):
        self.tracker.stop()

        self.assertEqual(self.store.save_calls, 1)


if __name__ == "__main__":
    unittest.main()
