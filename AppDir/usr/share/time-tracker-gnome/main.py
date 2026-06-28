#!/usr/bin/env python3
import os
import sys
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio

from store import DataStore
from tracker import TimeTracker


CSS = """
.tt-window {
    background-color: #fafafa;
    font-family: "Cantarell", "Inter", "Sans";
}
.tt-header {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 18px 24px;
}
.tt-header-title {
    font-size: 22px;
    font-weight: 800;
    color: #1c1c1c;
}
.tt-header-subtitle {
    font-size: 14px;
    color: #5e5e5e;
    margin-top: 4px;
}
.tt-session-time {
    font-size: 32px;
    font-weight: 700;
    color: #1c71d8;
    margin-top: 8px;
}
.tt-week-container {
    background-color: #fafafa;
    padding: 16px 24px;
}
.tt-day-row {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    border: 1px solid #e6e6e6;
}
.tt-day-row.today {
    border: 2px solid #1c71d8;
    background-color: #f0f5ff;
}
.tt-day-name {
    font-size: 15px;
    font-weight: 600;
    color: #1c1c1c;
}
.tt-day-date {
    font-size: 12px;
    color: #8c8c8c;
}
.tt-day-time {
    font-size: 16px;
    font-weight: 700;
    color: #1c71d8;
}
.tt-status {
    font-size: 12px;
    color: #8c8c8c;
    padding: 4px 24px;
}
.tt-quit-btn {
    background-color: #e01b24;
    color: #ffffff;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}
"""

DAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


class DayRow:
    def __init__(self):
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctx = self.box.get_style_context()
        ctx.add_class("tt-day-row")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box.pack_start(top, False, False, 0)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top.pack_start(left, True, True, 0)

        self.name_label = Gtk.Label()
        self.name_label.get_style_context().add_class("tt-day-name")
        self.name_label.set_halign(Gtk.Align.START)
        left.pack_start(self.name_label, False, False, 0)

        self.date_label = Gtk.Label()
        self.date_label.get_style_context().add_class("tt-day-date")
        self.date_label.set_halign(Gtk.Align.START)
        left.pack_start(self.date_label, False, False, 0)

        self.time_label = Gtk.Label()
        self.time_label.get_style_context().add_class("tt-day-time")
        self.time_label.set_halign(Gtk.Align.END)
        self.time_label.set_valign(Gtk.Align.CENTER)
        top.pack_start(self.time_label, False, False, 0)

        self.bar = Gtk.ProgressBar()
        self.bar.set_margin_top(8)
        self.bar.set_show_text(False)
        self.box.pack_start(self.bar, False, False, 0)

    def update(self, day_data, max_seconds):
        d = day_data["date"]
        ctx = self.box.get_style_context()
        if day_data["is_today"]:
            if not ctx.has_class("today"):
                ctx.add_class("today")
        else:
            if ctx.has_class("today"):
                ctx.remove_class("today")

        self.name_label.set_text(DAY_NAMES[d.weekday()])
        self.date_label.set_text(d.strftime("%d. %B"))
        self.time_label.set_text(format_duration(day_data["seconds"]))

        fraction = day_data["seconds"] / max_seconds if max_seconds > 0 else 0.0
        self.bar.set_fraction(min(fraction, 1.0))


class TimeTrackerApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.TimeTrackerGnome",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.store = DataStore()
        self.tracker = TimeTracker(self.store, on_tick=self.on_tracker_tick)
        self.window = None
        self.session_label = None
        self.status_label = None
        self.day_rows = []
        self._week_data = []

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self._setup_css()
        self.window = self._build_window()
        self.add_window(self.window)
        self.tracker.start()
        self.window.show_all()

    def _setup_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_window(self):
        win = Gtk.ApplicationWindow(application=self)
        win.set_title("Time Tracker")
        win.set_default_size(420, 580)
        win.set_icon_name("preferences-system-time")
        win.get_style_context().add_class("tt-window")
        win.connect("delete-event", self._on_delete_event)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        win.add(vbox)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header.get_style_context().add_class("tt-header")
        vbox.pack_start(header, False, False, 0)

        title = Gtk.Label(label="Time Tracker")
        title.get_style_context().add_class("tt-header-title")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Wochenübersicht")
        subtitle.get_style_context().add_class("tt-header-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header.pack_start(subtitle, False, False, 0)

        self.session_label = Gtk.Label(label="0m 00s")
        self.session_label.get_style_context().add_class("tt-session-time")
        self.session_label.set_halign(Gtk.Align.START)
        header.pack_start(self.session_label, False, False, 0)

        # Scrollable week list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scroll, True, True, 0)

        week_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        week_container.get_style_context().add_class("tt-week-container")
        scroll.add(week_container)

        self._week_data = self.store.get_week_data()
        max_seconds = max((d["seconds"] for d in self._week_data), default=1) or 1

        for day in self._week_data:
            row = DayRow()
            row.update(day, max_seconds)
            week_container.pack_start(row.box, False, False, 0)
            self.day_rows.append(row)

        # Bottom bar
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom.set_margin_bottom(8)
        bottom.set_margin_top(4)
        vbox.pack_start(bottom, False, False, 0)

        self.status_label = Gtk.Label(label="Tracking aktiv")
        self.status_label.get_style_context().add_class("tt-status")
        self.status_label.set_halign(Gtk.Align.START)
        bottom.pack_start(self.status_label, True, True, 0)

        quit_btn = Gtk.Button(label="Beenden")
        quit_btn.get_style_context().add_class("tt-quit-btn")
        quit_btn.set_margin_right(24)
        quit_btn.connect("clicked", self._on_quit)
        bottom.pack_end(quit_btn, False, False, 0)

        return win

    def _on_delete_event(self, widget, event):
        # Hide window instead of destroying it so tracking keeps running
        self.window.hide()
        return True

    def _on_quit(self, button):
        self.quit()

    def on_tracker_tick(self):
        GLib.idle_add(self._update_ui)

    def _update_ui(self):
        self.session_label.set_text(format_duration(int(self.tracker.session_seconds)))

        if self.tracker.is_afk:
            self.status_label.set_text("AFK – Zeit wird nicht gezählt")
        else:
            self.status_label.set_text("Tracking aktiv")

        # Refresh week view every ~30s to avoid constant churn
        secs = int(self.tracker.session_seconds)
        if secs % 30 == 0:
            self._week_data = self.store.get_week_data()
            max_seconds = max((d["seconds"] for d in self._week_data), default=1) or 1
            for row, day in zip(self.day_rows, self._week_data):
                row.update(day, max_seconds)

        return False

    def do_shutdown(self):
        self.tracker.stop()
        self.tracker.join(timeout=2)
        super().do_shutdown()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = TimeTrackerApp()

    def _on_sigterm(signum, frame):
        app.quit()

    signal.signal(signal.SIGTERM, _on_sigterm)
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
