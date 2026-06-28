import json
import os
from datetime import date, timedelta


class DataStore:
    def __init__(self):
        self.dir = os.path.expanduser("~/.local/share/time-tracker-gnome")
        self.path = os.path.join(self.dir, "data.json")
        os.makedirs(self.dir, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            pass

    def add_seconds(self, day_key: str, seconds: int):
        if day_key not in self.data:
            self.data[day_key] = 0
        self.data[day_key] += seconds
        self._save()

    def get_seconds(self, day_key: str) -> int:
        return self.data.get(day_key, 0)

    def get_week_data(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week = []
        for i in range(7):
            d = monday + timedelta(days=i)
            key = d.isoformat()
            week.append({
                "date": d,
                "key": key,
                "seconds": self.get_seconds(key),
                "is_today": d == today,
            })
        return week
