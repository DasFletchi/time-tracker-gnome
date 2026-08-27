import threading
import time
from datetime import date

try:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib
except (ImportError, ValueError):
    # The packaged application includes PyGObject. Keeping this optional makes
    # the non-graphical storage tests usable on minimal development systems.
    Gio = None
    GLib = None

from store import DataStore


AFK_THRESHOLD_MS = 120_000  # 2 minutes
TICK_SECONDS = 5
MAX_ELAPSED_PER_TICK = 15  # cap to handle suspend/resume gracefully
SAVE_INTERVAL_SECONDS = 60  # reduce disk writes while limiting data loss on crashes
IDLE_MONITOR_BUS_NAME = "org.gnome.Mutter.IdleMonitor"
IDLE_MONITOR_OBJECT_PATH = "/org/gnome/Mutter/IdleMonitor/Core"
IDLE_MONITOR_INTERFACE = "org.gnome.Mutter.IdleMonitor"

_idle_monitor_connection = None


def get_idle_time_ms() -> int:
    """Liest die GNOME-Leerlaufzeit ohne für jede Abfrage einen Prozess zu starten."""
    global _idle_monitor_connection

    if Gio is None or GLib is None:
        return 0

    try:
        if _idle_monitor_connection is None:
            _idle_monitor_connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        result = _idle_monitor_connection.call_sync(
            IDLE_MONITOR_BUS_NAME,
            IDLE_MONITOR_OBJECT_PATH,
            IDLE_MONITOR_INTERFACE,
            "GetIdletime",
            None,
            GLib.VariantType.new("(t)"),
            Gio.DBusCallFlags.NONE,
            2_000,
            None,
        )
        return int(result.unpack()[0])
    except Exception:
        # Reconnect after a session-bus or Mutter restart. Returning zero keeps
        # the tracker functional on desktops without the GNOME idle monitor.
        _idle_monitor_connection = None
        return 0


class TimeTracker(threading.Thread):
    def __init__(
        self,
        store: DataStore,
        on_tick=None,
        save_interval_seconds: int = SAVE_INTERVAL_SECONDS,
    ):
        super().__init__(daemon=True)
        self.store = store
        self.on_tick = on_tick
        self.save_interval_seconds = save_interval_seconds
        self._running = True
        self.today_key = date.today().isoformat()
        self.session_seconds = 0
        self.last_tick = time.monotonic()
        self.last_save = self.last_tick
        self.last_idle_ms = 0
        self.is_afk = False

    def _save_if_due(self, now: float) -> None:
        """Schreibt gepufferte Zeiten höchstens einmal pro Speicherintervall."""
        if now - self.last_save >= self.save_interval_seconds:
            if self.store.save():
                self.last_save = now

    def run(self):
        while self._running:
            now = time.monotonic()
            elapsed = now - self.last_tick
            self.last_tick = now

            # Cap elapsed time to avoid counting sleep/suspend as active time
            if elapsed > MAX_ELAPSED_PER_TICK:
                elapsed = TICK_SECONDS

            self.last_idle_ms = get_idle_time_ms()
            self.is_afk = self.last_idle_ms >= AFK_THRESHOLD_MS

            if not self.is_afk:
                self.session_seconds += elapsed
                self.store.add_seconds(self.today_key, max(1, round(elapsed)))

            self._save_if_due(now)

            # Handle day rollover
            current_key = date.today().isoformat()
            if current_key != self.today_key:
                self.today_key = current_key
                self.session_seconds = 0
                # Trigger immediate UI refresh so week view updates
                if self.on_tick:
                    try:
                        self.on_tick()
                    except Exception:
                        pass

            if self.on_tick:
                try:
                    self.on_tick()
                except Exception:
                    pass

            time.sleep(TICK_SECONDS)

    def stop(self):
        self._running = False
        # A normal quit persists the most recent seconds immediately. Only an
        # unexpected power loss can leave at most one save interval unsaved.
        self.store.save()
