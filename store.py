import json
import os
import tempfile
import threading
import time
from datetime import date, timedelta
from typing import Dict, Optional, Tuple


EXTERNAL_EDIT_CHECK_SECONDS = 60


class DataStore:
    """Speichert tägliche Tracking-Zeiten in einer einfach editierbaren JSON-Datei.

    Das Dateiformat ist bewusst flach gehalten: Jeder Schlüssel ist ein Datum im
    ISO-Format (YYYY-MM-DD), jeder Wert die Anzahl der Sekunden für diesen Tag.
    Änderungen, die während des Trackings manuell in der Datei gespeichert werden,
    werden vor dem nächsten Schreibvorgang automatisch eingelesen.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.expanduser(
            "~/.local/share/time-tracker-gnome/data.json"
        )
        self.dir = os.path.dirname(self.path)
        os.makedirs(self.dir, exist_ok=True)

        self._lock = threading.RLock()
        loaded_data = self._read_file()
        self.data: Dict[str, int] = loaded_data if loaded_data is not None else {}
        self._file_signature = self._get_file_signature()
        self._last_external_check = time.monotonic()
        self._pending_seconds: Dict[str, int] = {}

    def _get_file_signature(self) -> Optional[Tuple[int, int]]:
        """Liefert eine Kennung für die aktuelle Dateiversion oder None."""
        try:
            stat = os.stat(self.path)
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    @staticmethod
    def _normalise_data(raw_data) -> Dict[str, int]:
        """Akzeptiert nur Datumsschlüssel und nicht-negative Ganzzahlsekunden."""
        if not isinstance(raw_data, dict):
            return {}

        clean_data: Dict[str, int] = {}
        for key, value in raw_data.items():
            if not isinstance(key, str) or isinstance(value, bool):
                continue
            try:
                date.fromisoformat(key)
                seconds = int(value)
            except (TypeError, ValueError):
                continue
            if seconds >= 0:
                clean_data[key] = seconds
        return clean_data

    def _read_file(self) -> Optional[Dict[str, int]]:
        try:
            with open(self.path, "r", encoding="utf-8") as data_file:
                return self._normalise_data(json.load(data_file))
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError):
            # A partially written or invalid manual edit must never erase the
            # last valid in-memory values.
            return None

    def _reload_if_changed_locked(self, force: bool = False) -> None:
        """Übernimmt eine von außen gespeicherte, gültige JSON-Datei.

        Die Dateimetadaten werden im Normalbetrieb nur einmal pro Minute geprüft.
        Vor einem eigenen Schreibvorgang wird die Prüfung immer erzwungen, damit
        manuelle Änderungen keinesfalls überschrieben werden. Noch nicht
        gespeicherte Tracking-Sekunden werden anschließend wieder ergänzt.
        """
        now = time.monotonic()
        if not force and now - self._last_external_check < EXTERNAL_EDIT_CHECK_SECONDS:
            return

        self._last_external_check = now
        current_signature = self._get_file_signature()
        if current_signature != self._file_signature:
            external_data = self._read_file()
            if external_data is not None:
                self.data = external_data
                for day_key, seconds in self._pending_seconds.items():
                    self.data[day_key] = self.data.get(day_key, 0) + seconds
                self._file_signature = current_signature

    def _save_locked(self) -> bool:
        """Schreibt JSON atomar, damit die Datei nie halb geschrieben vorliegt."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.dir,
                prefix=".data-",
                suffix=".json",
                delete=False,
            ) as temp_file:
                temp_path = temp_file.name
                json.dump(self.data, temp_file, indent=2, sort_keys=True)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.path)
            self._file_signature = self._get_file_signature()
            self._last_external_check = time.monotonic()
            return True
        except OSError:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False

    def add_seconds(self, day_key: str, seconds: int) -> None:
        """Puffert aktive Sekunden im Speicher bis zum nächsten Speichern."""
        if seconds <= 0:
            return
        with self._lock:
            self._reload_if_changed_locked()
            seconds = int(seconds)
            self.data[day_key] = self.data.get(day_key, 0) + seconds
            self._pending_seconds[day_key] = (
                self._pending_seconds.get(day_key, 0) + seconds
            )

    def save(self) -> bool:
        """Speichert alle gepufferten Sekunden und gibt den Erfolg zurück."""
        with self._lock:
            self._reload_if_changed_locked(force=True)
            if not self._pending_seconds:
                return True
            if self._save_locked():
                self._pending_seconds.clear()
                return True
            return False

    def get_seconds(self, day_key: str) -> int:
        with self._lock:
            self._reload_if_changed_locked()
            return self.data.get(day_key, 0)

    def get_week_data(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        with self._lock:
            self._reload_if_changed_locked()
            return [
                {
                    "date": current_date,
                    "key": current_date.isoformat(),
                    "seconds": self.data.get(current_date.isoformat(), 0),
                    "is_today": current_date == today,
                }
                for current_date in (monday + timedelta(days=index) for index in range(7))
            ]
