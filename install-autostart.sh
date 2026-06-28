#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/time-tracker-gnome.desktop" <<EOF
[Desktop Entry]
Name=Time Tracker
Comment=Einfache Bildschirmzeit-Tracking-App mit Wochenansicht
Exec=$SCRIPT_DIR/run.sh
Icon=preferences-system-time
Type=Application
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Autostart-Datei installiert in $AUTOSTART_DIR/time-tracker-gnome.desktop"
