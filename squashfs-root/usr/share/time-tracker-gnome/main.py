#! usr/bin/env python3
import os
import sys
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from store import DataStore
from tracker import TimeTracker

# CSS stylesheet for OLED Black theme
CSS = """
window, .background {
    background-color: #000000;
}
.tt-window {
    background-color: #000000;
}
headerbar {
    background-color: #000000;
    border-bottom: 1px solid #1c1c1c;
    color: #ffffff;
}
clamp {
    background-color: #000000;
}
scrolledwindow {
    background-color: #000000;
}
viewport {
    background-color: #000000;
}
.tt-header-box {
    background-color: #000000;
    padding: 24px;
    border-bottom: 1px solid #1c1c1c;
}
.tt-header-title {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
}
.tt-header-subtitle {
    font-size: 14px;
    color: #888888;
    margin-top: 4px;
}
.tt-session-time {
    font-size: 38px;
    font-weight: 800;
    color: #3584e4;
    margin-top: 8px;
}
.tt-week-container {
    background-color: #000000;
    padding: 16px 24px;
}
.tt-day-row {
    background-color: #101010;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    border: 1px solid #202020;
}
.tt-day-row.today {
    border: 2px solid #3584e4;
    background-color: #081220;
}
.tt-day-name {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
}
.tt-day-date {
    font-size: 13px;
    color: #888888;
}
.tt-day-time {
    font-size: 16px;
    font-weight: 700;
    color: #3584e4;
}
progressbar {
    margin-top: 8px;
}
progressbar trough {
    background-color: #202020;
    border-radius: 6px;
    min-height: 8px;
}
progressbar progress {
    background-color: #3584e4;
    border-radius: 6px;
    min-height: 8px;
}
.tt-status {
    font-size: 13px;
    color: #888888;
    padding: 12px 24px;
}
.tt-quit-btn {
    background-color: #c01c28;
    color: #ffffff;
    border-radius: 8px;
    font-weight: 600;
    margin-right: 24px;
    padding: 6px 16px;
}
.tt-quit-btn:hover {
    background-color: #e01b24;
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


class DayRow(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("tt-day-row")

        # Top row (Horizontal)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(top)

        # Left column (Vertical)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        left.set_hexpand(True)
        top.append(left)

        self.name_label = Gtk.Label()
        self.name_label.add_css_class("tt-day-name")
        self.name_label.set_halign(Gtk.Align.START)
        left.append(self.name_label)

        self.date_label = Gtk.Label()
        self.date_label.add_css_class("tt-day-date")
        self.date_label.set_halign(Gtk.Align.START)
        left.append(self.date_label)

        # Right column
        self.time_label = Gtk.Label()
        self.time_label.add_css_class("tt-day-time")
        self.time_label.set_halign(Gtk.Align.END)
        self.time_label.set_valign(Gtk.Align.CENTER)
        top.append(self.time_label)

        # Progress bar
        self.bar = Gtk.ProgressBar()
        self.bar.set_margin_top(8)
        self.bar.set_show_text(False)
        self.append(self.bar)

    def update(self, day_data, max_seconds):
        d = day_data["date"]
        if day_data["is_today"]:
            if not self.has_css_class("today"):
                self.add_css_class("today")
        else:
            if self.has_css_class("today"):
                self.remove_css_class("today")

        self.name_label.set_text(DAY_NAMES[d.weekday()])
        self.date_label.set_text(d.strftime("%d. %B"))
        self.time_label.set_text(format_duration(day_data["seconds"]))

        fraction = day_data["seconds"] / max_seconds if max_seconds > 0 else 0.0
        self.bar.set_fraction(min(fraction, 1.0))


class TimeTrackerApp(Adw.Application):
    def __init__(self, is_background=False):
        super().__init__(
            application_id="com.fletchi.TimeTrackerGnome",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.is_background = is_background
        self.store = DataStore()
        self.tracker = TimeTracker(self.store, on_tick=self.on_tracker_tick)
        self.window = None
        self.session_label = None
        self.status_label = None
        self.day_rows = []
        self._week_data = []

    def do_startup(self):
        super().do_startup()
        self.hold()  # Keeps application running when window is closed/hidden

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self._setup_css()
        self.window = self._build_window()
        self.add_window(self.window)
        self.tracker.start()

        # Setup autostart automatically
        self.setup_autostart()

        if not self.is_background:
            self.window.present()
        else:
            print("Time Tracker gestartet im Hintergrund...")
            # We reset this so subsequent user clicks on the application launcher will open the UI
            self.is_background = False

    def _setup_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Force dark mode using Libadwaita StyleManager
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def _build_window(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_title("Time Tracker")
        win.set_default_size(420, 600)
        win.connect("close-request", self._on_close_request)

        toolbar_view = Adw.ToolbarView()
        win.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(vbox)

        clamp = Adw.Clamp()
        clamp.set_child(scroll)
        toolbar_view.set_content(clamp)

        # Header card (Session Tracker)
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_box.add_css_class("tt-header-box")
        vbox.append(header_box)

        title = Gtk.Label(label="Time Tracker")
        title.add_css_class("tt-header-title")
        title.set_halign(Gtk.Align.START)
        header_box.append(title)

        subtitle = Gtk.Label(label="Wochenübersicht")
        subtitle.add_css_class("tt-header-subtitle")
        subtitle.set_halign(Gtk.Align.START)
        header_box.append(subtitle)

        self.session_label = Gtk.Label(label="0m 00s")
        self.session_label.add_css_class("tt-session-time")
        self.session_label.set_halign(Gtk.Align.START)
        header_box.append(self.session_label)

        # Week container
        week_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        week_container.add_css_class("tt-week-container")
        vbox.append(week_container)

        self._week_data = self.store.get_week_data()
        max_seconds = max((d["seconds"] for d in self._week_data), default=1) or 1

        for day in self._week_data:
            row = DayRow()
            row.update(day, max_seconds)
            week_container.append(row)
            self.day_rows.append(row)

        # Bottom bar
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom.set_margin_bottom(12)
        bottom.set_margin_top(8)
        vbox.append(bottom)

        self.status_label = Gtk.Label(label="Tracking aktiv")
        self.status_label.add_css_class("tt-status")
        self.status_label.set_halign(Gtk.Align.START)
        bottom.append(self.status_label)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bottom.append(spacer)

        quit_btn = Gtk.Button(label="Beenden")
        quit_btn.add_css_class("tt-quit-btn")
        quit_btn.connect("clicked", self._on_quit)
        bottom.append(quit_btn)

        return win

    def _on_close_request(self, widget):
        # Hide window instead of destroying it so tracking keeps running in background
        self.window.hide()
        return True

    def _on_quit(self, button):
        self.quit()

    def on_tracker_tick(self):
        GLib.idle_add(self._update_ui)

    def _update_ui(self):
        if not self.session_label or not self.status_label:
            return False

        self.session_label.set_text(format_duration(int(self.tracker.session_seconds)))

        if self.tracker.is_afk:
            self.status_label.set_text("AFK – Zeit wird nicht gezählt")
        else:
            self.status_label.set_text("Tracking aktiv")

        # Refresh week view every ~30s
        secs = int(self.tracker.session_seconds)
        if secs % 30 == 0:
            self._week_data = self.store.get_week_data()
            max_seconds = max((d["seconds"] for d in self._week_data), default=1) or 1
            for row, day in zip(self.day_rows, self._week_data):
                row.update(day, max_seconds)

        return False

    def setup_autostart(self):
        appimage_path = os.environ.get("APPIMAGE")
        if not appimage_path:
            # Fallback to dev run.sh path if running locally
            fallback = os.path.abspath(os.path.join(os.path.dirname(__file__), "run.sh"))
            if os.path.exists(fallback):
                appimage_path = fallback
            else:
                return

        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        desktop_file = os.path.join(autostart_dir, "time-tracker-gnome.desktop")

        content = f"""[Desktop Entry]
Name=Time Tracker
Comment=Bildschirmzeit-Tracking-App
Exec="{appimage_path}" --background
Icon=preferences-system-time
Type=Application
Terminal=false
X-GNOME-Autostart-enabled=true
"""
        try:
            with open(desktop_file, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(desktop_file, 0o755)
            print(f"Autostart-Datei eingerichtet in {desktop_file}")
        except Exception as e:
            print(f"Fehler beim Einrichten von Autostart: {e}")

    def do_shutdown(self):
        self.tracker.stop()
        self.tracker.join(timeout=2)
        super().do_shutdown()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    is_background = False
    if "--background" in sys.argv:
        is_background = True
        sys.argv.remove("--background")

    app = TimeTrackerApp(is_background=is_background)

    def _on_sigterm(signum, frame):
        app.quit()

    signal.signal(signal.SIGTERM, _on_sigterm)
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
