# Time Tracker GNOME

A simple, background-running screen time tracking app in GNOME style.

## Features

- **Week Overview** – Daily screen time for the current week with progress bars
- **AFK Mode** – Time is not counted when mouse/keyboard are idle for 2 minutes (uses GNOME IdleMonitor D-Bus)
- **Suspend Safe** – System sleep time is not counted as active time
- **Runs in Background** – Close the window, tracking keeps running
- **Autostart** – Automatically registers itself on first launch

## Quick Start

### AppImage (recommended)

Download the latest AppImage from the [Releases](https://github.com/DasFletchi/time-tracker-gnome/releases) page:

```bash
chmod +x "Time Tracker-1.0.0-x86_64.AppImage"
./"Time Tracker-1.0.0-x86_64.AppImage"
```

Autostart is set up automatically on first run.

### Run from source

```bash
git clone https://github.com/DasFletchi/time-tracker-gnome.git
cd time-tracker-gnome
./run.sh
```

### Build AppImage yourself

```bash
pip install appimage-builder
export APPDIR=./AppDir
appimage-builder --recipe AppImageBuilder.yml
```

## Data

Tracking data is stored in `~/.local/share/time-tracker-gnome/data.json`.

## Requirements

- GNOME 42+ (or any libadwaita-compatible desktop)
- Python 3 + PyGObject
- GTK 4 + libadwaita
