import threading
import time
import subprocess
from datetime import date
from store import DataStore


AFK_THRESHOLD_MS = 120_000  # 2 minutes
TICK_SECONDS = 1
MAX_ELAPSED_PER_TICK = 5  # cap to handle suspend/resume gracefully


def get_idle_time_ms() -> int:
    try:
        result = subprocess.run(
            [
                "dbus-send",
                "--print-reply",
                "--dest=org.gnome.Mutter.IdleMonitor",
                "/org/gnome/Mutter/IdleMonitor/Core",
                "org.gnome.Mutter.IdleMonitor.GetIdletime",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            for i, part in enumerate(parts):
                if part == "uint64":
                    return int(parts[i + 1])
    except Exception:
        pass
    return 0


class TimeTracker(threading.Thread):
    def __init__(self, store: DataStore, on_tick=None):
        super().__init__(daemon=True)
        self.store = store
        self.on_tick = on_tick
        self._running = True
        self.today_key = date.today().isoformat()
        self.session_seconds = 0
        self.last_tick = time.monotonic()
        self.last_idle_ms = 0
        self.is_afk = False

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
                self.store.add_seconds(self.today_key, int(elapsed))

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
