# Time Tracker GNOME

**Time Tracker GNOME** erfasst die aktive Bildschirmzeit und zeigt die aktuelle Woche in einer schlanken GNOME-Oberfläche an. Die Version **1.1.1** trennt die Zeitmessung vollständig vom Anwendungsfenster: Das Schließen des Fensters blendet nur die Oberfläche aus; das Tracking bleibt aktiv, bis die Anwendung bewusst über **Beenden** oder durch das Betriebssystem beendet wird.

| Funktion | Verhalten |
|---|---|
| Wochenübersicht | Zeigt die täglichen Zeiten der laufenden Woche mit Balken an. |
| AFK-Erkennung | Bei mindestens zwei Minuten ohne Maus- oder Tastatureingabe wird keine Zeit erfasst. |
| Ruhezustand | Schlaf- und Suspend-Zeiten werden nicht als aktive Bildschirmzeit gezählt. |
| Hintergrundmodus | Der Autostart startet ohne Fenster; ein späterer Programmstart öffnet die Oberfläche. |
| JSON-Bearbeitung | Tageswerte können direkt in einer verständlichen JSON-Datei angepasst werden. |

## Starten

Die aktuelle AppImage-Version kann über die [Releases](https://github.com/DasFletchi/time-tracker-gnome/releases) bezogen werden. Nach dem Herunterladen wird sie ausführbar gemacht und normal gestartet.

```bash
chmod +x "Time Tracker-1.1.1-x86_64.AppImage"
./"Time Tracker-1.1.1-x86_64.AppImage"
```

Für die Ausführung aus dem Quellcode werden Python 3, PyGObject, GTK 4 und libadwaita benötigt. Das Startskript reicht zusätzliche Argumente unverändert weiter; daher kann der Hintergrundmodus zum Testen explizit gestartet werden.

```bash
git clone https://github.com/DasFletchi/time-tracker-gnome.git
cd time-tracker-gnome
./run.sh
./run.sh --background
```

## Zeitdaten manuell bearbeiten

Die Tracking-Daten liegen in der Datei `~/.local/share/time-tracker-gnome/data.json`. Sie enthält nur Datumsschlüssel im ISO-Format `YYYY-MM-DD` und die jeweilige aktive Zeit in **Sekunden**. Die Struktur ist absichtlich einfach, damit sie mit jedem Texteditor angepasst werden kann.

```json
{
  "2026-08-24": 12600,
  "2026-08-25": 16200,
  "2026-08-26": 7200
}
```

| Wert | Bedeutung |
|---|---|
| `"2026-08-26"` | Das Datum, dessen Bildschirmzeit bearbeitet wird. |
| `7200` | Die gespeicherte Bildschirmzeit in Sekunden; `7200` entspricht zwei Stunden. |

Speichere die Datei nach einer Änderung als **gültiges JSON**. Die Anwendung erkennt externe Speicherungen vor dem nächsten Schreibvorgang, übernimmt die neuen Werte und zählt anschließend ab dem bearbeiteten Wert weiter. Ungültige Schlüssel, negative Werte und ungültiges JSON werden ignoriert, um die Datenablage zu schützen. Beim Speichern schreibt die Anwendung atomar, sodass keine unvollständige JSON-Datei entsteht.

Eine kopierbare Vorlage liegt als [`data.example.json`](./data.example.json) im Repository. Neue Tage können jederzeit als weitere Zeile ergänzt werden.

> Die JSON-Datei kann auch während die Anwendung läuft bearbeitet werden. Speichere die Änderung jedoch vollständig in deinem Editor, bevor du die Datei schließt.

## Hintergrundbetrieb und Autostart

Der Autostart wird beim ersten Programmstart automatisch angelegt und verwendet den Parameter `--background`. Er ist mit `NoDisplay=true` als reiner Hintergrunddienst markiert und erscheint deshalb nicht als irreführender zweiter Eintrag im Pop!_OS- beziehungsweise GNOME-App-Menü. In diesem Modus beginnt die Erfassung direkt beim Start, ohne ein Fenster zu erzeugen. Wird anschließend der reguläre Eintrag **Time Tracker** im App-Menü ausgewählt, öffnet dieselbe laufende Instanz die Oberfläche.

Das Schließen über das Fenstersymbol **beendet die Anwendung nicht**. Es versteckt ausschließlich das Fenster. Nur der rote Knopf **Beenden**, ein Abmelden/Herunterfahren oder ein bewusstes Beenden des Prozesses stoppt die Messung.

Für eine Quellcode-Installation kann der Autostart auch manuell eingerichtet werden:

```bash
./install-autostart.sh
```

## AppImage bauen

Zum Erstellen eines neuen AppImage wird das mit dem Projekt gelieferte `appimagetool` verwendet. Es verarbeitet den vorhandenen `AppRun`-Starter direkt und vermeidet damit den inkompatiblen `appimage-builder`-Pfad.

```bash
rm -rf AppDir/usr/share/time-tracker-gnome
mkdir -p AppDir/usr/share/time-tracker-gnome
cp main.py store.py tracker.py AppDir/usr/share/time-tracker-gnome/
chmod +x AppDir/AppRun AppDir/usr/bin/time-tracker-gnome
ARCH=x86_64 ./appimagetool AppDir "Time-Tracker-1.1.1-x86_64.AppImage"
```

## Entwicklung und Tests

Die Speicherung kann ohne grafische Sitzung geprüft werden:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py store.py tracker.py
```
