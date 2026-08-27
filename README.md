# Time Tracker GNOME

**Time Tracker GNOME** erfasst die aktive Bildschirmzeit und zeigt die aktuelle Woche in einer schlanken GNOME-Oberfläche an. Die Version **1.1.3** trennt die Zeitmessung vollständig vom Anwendungsfenster: Das Schließen des Fensters blendet nur die Oberfläche aus; das Tracking bleibt aktiv, bis die Anwendung bewusst über **Beenden** oder durch das Betriebssystem beendet wird.

| Funktion | Verhalten |
|---|---|
| Wochenübersicht | Zeigt die täglichen Zeiten der laufenden Woche mit Balken an. |
| AFK-Erkennung | Bei mindestens zwei Minuten ohne Maus- oder Tastatureingabe wird keine Zeit erfasst. |
| Ruhezustand | Schlaf- und Suspend-Zeiten werden nicht als aktive Bildschirmzeit gezählt. |
| Hintergrundmodus | Der Autostart startet ohne Fenster; ein späterer Programmstart öffnet die Oberfläche. |
| JSON-Bearbeitung | Tageswerte können direkt in einer verständlichen JSON-Datei angepasst werden. |
| SSD-schonendes Speichern | Neue Zeitwerte werden im Speicher gesammelt und höchstens einmal pro Minute atomar in die JSON-Datei geschrieben. |
| CPU-schonende Erfassung | Die GNOME-Leerlaufzeit wird nur noch alle fünf statt jede Sekunde abgefragt. |
| Effizienter Hintergrundmodus | Bei geschlossenem Fenster werden keine GTK-Aktualisierungen eingeplant. |

## Starten

Die aktuelle AppImage-Version kann über die [Releases](https://github.com/DasFletchi/time-tracker-gnome/releases) bezogen werden. Nach dem Herunterladen wird sie ausführbar gemacht und normal gestartet.

```bash
chmod +x "Time Tracker-1.1.3-x86_64.AppImage"
./"Time Tracker-1.1.3-x86_64.AppImage"
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

Aktive Sekunden werden zuerst nur im Arbeitsspeicher gesammelt. Die Anwendung speichert höchstens **einmal pro Minute** auf das Laufwerk und speichert außerdem sofort bei einem regulären Beenden. Das reduziert die Zahl der JSON-Schreibvorgänge gegenüber dem früheren Verhalten um den Faktor 60. Nur bei einem Stromausfall oder erzwungenen Beenden können höchstens ungefähr die letzten 60 Sekunden verlorengehen. Die Prüfung auf eine manuell geänderte Datei erfolgt ebenfalls nur einmal pro Minute, wird vor dem eigenen Speichern jedoch immer erzwungen.

Die Erfassung fragt den GNOME-Leerlaufdienst nur noch alle fünf Sekunden ab. Dadurch sinken die regelmäßigen Prozessstarts und Hintergrundaufweckungen von maximal 86.400 auf 17.280 pro Tag. Das Schließen der Oberfläche spart zusätzlich GTK-Aktualisierungen; beim erneuten Öffnen werden die aktuellen Werte sofort angezeigt.

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
ARCH=x86_64 ./appimagetool AppDir "Time-Tracker-1.1.3-x86_64.AppImage"
```

## Entwicklung und Tests

Die Speicherung kann ohne grafische Sitzung geprüft werden:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py store.py tracker.py
```
