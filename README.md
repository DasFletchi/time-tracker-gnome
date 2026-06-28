# Time Tracker GNOME

Eine einfache, im Hintergrund laufende Bildschirmzeit-Tracking-App im GNOME-Stil.

## Features

- **Wochenansicht** – Übersicht über die tägliche Bildschirmzeit der aktuellen Woche
- **AFK-Modus** – Zeit wird nicht gezählt, wenn Maus/Tastatur 2 Minuten lang nicht benutzt werden (über GNOME IdleMonitor D-Bus)
- **Suspend-sicher** – System-Sleep-Zeit wird nicht als aktive Zeit gezählt
- **Im Hintergrund laufen** – Das Fenster lässt sich schließen, das Tracking läuft weiter
- **Autostart** – optional bei GNOME-Login automatisch starten

## Starten

```bash
cd time-tracker-gnome
./run.sh
```

## Autostart einrichten

```bash
./install-autostart.sh
```

## Daten

Die Zeiten werden in `~/.local/share/time-tracker-gnome/data.json` gespeichert.
