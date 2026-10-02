# MAKO-Assistent — Funktionsübersicht

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · **Deutsch** · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

Der **MAKO-Assistent** ist ein grafisches Linux-Desktop-Werkzeug, mit dem du die **Frame-Generierung von MAKO Renderer (Mako FG)** für deine Steam-Spiele per Klick ein- oder ausschaltest, ohne Konfigurationsdateien von Hand zu bearbeiten.

## Für wen ist das gedacht?

Auf dem Steam Deck gibt es im Spielmodus das Decky-Plugin von MAKO, mit dem du alles direkt im Spiel einstellen kannst. Auf einem **normalen Linux-Desktop-PC oder Laptop** (zum Beispiel Arch, Fedora oder Ubuntu mit KDE Plasma oder GNOME) musst du für jedes Spiel, das MAKO nutzen soll, normalerweise alles von Hand erledigen:

1. In Steam unter „Eigenschaften → Startoptionen“ `~/.local/bin/mako-launch %command%` eintragen, ohne die vorhandenen Optionen zu zerstören.
2. Herausfinden, welches Programm das Spiel **tatsächlich ausführt** (viele Spiele starten zuerst einen Launcher, Unreal-Engine-Spiele eine `*-Shipping.exe`).
3. In den MAKO-Einstellungen ein Spielprofil anlegen und die richtigen zugeordneten Prozesse (`active_in`) eintragen.
4. Alles wiederholen, wenn ein Spiel-Update Pfad oder Namen der ausführbaren Datei ändert.
5. Und selbst wenn das Spiel läuft, weißt du nicht sicher, ob die Frame-Generierung wirklich arbeitet.

Der MAKO-Assistent fasst diese Schritte zu einem einzigen Knopf zusammen und zeigt dir, während ein Spiel läuft, welche MAKO-Funktionen **tatsächlich** aktiv sind.

## Voraussetzungen

> ⚠ **Der MAKO-Assistent enthält MAKO Renderer nicht und installiert ihn auch nicht.** Er verwaltet nur die Einstellungen von MAKO.

Erledige zuerst Folgendes:

1. **MAKO Renderer (Standalone) installieren**, nach der Installationsanleitung von MAKO selbst. Danach sollte `~/.local/bin/mako-launch` vorhanden sein.
2. **MAKO UI einmal öffnen**, damit die Standardeinstellungen angelegt werden. Dabei entstehen `~/.config/mako-render/conf.toml` und das Standardprofil `mako`. Jedes Spielprofil, das der MAKO-Assistent anlegt, ist eine Kopie dieses Standardprofils.
3. **Steam installieren.** Unterstützt werden das native Paket (`~/.local/share/Steam`, `~/.steam`) sowie die Flatpak- und Snap-Version.

Erst wenn all das erledigt ist und MAKO selbst funktioniert, solltest du mit dem MAKO-Assistenten Mako FG für ein Spiel installieren.

Optional: **Decky Loader.** Damit lassen sich Startoptionen live übernehmen, während Steam läuft, ohne Steam zu schließen (siehe „So werden Startoptionen geschrieben“ unten).

## Funktionen

### 1. Automatisches Einlesen der Steam-Bibliothek

- Beim ersten Start werden **alle** Steam-Bibliotheken eingelesen (auch Bibliotheken auf anderen Laufwerken). Danach kannst du auf „⟳ Steam-Spiele neu einlesen“ klicken.
- Werkzeuge wie Proton und die Steam Linux Runtime werden ausgeblendet, es erscheinen nur Spiele.
- Spielnamen werden im offiziellen lokalisierten Steam-Namen deiner Oberflächensprache angezeigt und so sortiert, wie es in dieser Sprache üblich ist.
- Zu jedem Spiel siehst du das Titelbild, die aktuellen Startoptionen, das MAKO-Profil und die erkannten Pfade der ausführbaren Datei.

### 2. „Mako FG installieren“ mit einem Klick

Ein Klick auf „Mako FG installieren“ bewirkt Folgendes:

- **Startoption eintragen**: `~/.local/bin/mako-launch %command%` wird in die Steam-Startoptionen eingefügt, **vorhandene Einträge bleiben erhalten**. Aus `FOO=1 %command% -dx11` wird zum Beispiel `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Die echte ausführbare Datei erkennen**: anhand der App-Informationen von Steam. Launcher werden berücksichtigt (stattdessen wird das eigentliche Spielprogramm im Installationsordner gesucht), ebenso `*-Shipping.exe` von Unreal Engine; gängige Hilfsprogramme werden übersprungen.
- **MAKO-Spielprofil anlegen**: Das Standardprofil `mako` wird in `conf.toml` als eigenes Profil für das Spiel kopiert, und die Profil-Metadaten von MAKO werden geschrieben. **MAKO UI und das Decky-Plugin sehen dieses Profil und können es direkt bearbeiten.**
- **Doppelte Zuordnungen vermeiden**: Ordnet auch das Standardprofil `mako` die ausführbare Datei dieses Spiels zu, wird sie aus `mako` entfernt, sodass das Spiel nur sein eigenes Profil verwendet. Ordnet das Profil eines anderen Spiels dieselbe Datei zu, erhältst du einen Hinweis, aber es wird nichts automatisch geändert.

### 3. So werden Startoptionen geschrieben

Steam liest Startoptionen nur beim Start und überschreibt seine Konfigurationsdatei beim Beenden. Damit Steam deine Änderung nicht überschreibt, wählt der MAKO-Assistent die Schreibmethode je nach Zustand von Steam und zeigt diesen Zustand im Fenster an:

| Zustand von Steam | Schreibmethode |
|---|---|
| Läuft nicht | Bearbeitet Steams `localconfig.vdf` direkt (nach einer Sicherung) |
| Läuft, und der Steam-Client ist erreichbar (benötigt Decky Loader) | Übernimmt die Änderung live über den Steam-Client, ohne Steam neu zu starten |
| Läuft, aber der Client ist nicht erreichbar | Fragt, ob Steam geschlossen werden soll → übernimmt die Änderung → startet Steam neu |

### 4. Entfernen

- „Entfernen“ nimmt nur `mako-launch` aus den Startoptionen heraus; deine übrigen Optionen bleiben unverändert.
- Die MAKO-Einstellungen des Spiels bleiben **standardmäßig erhalten**, damit du sie bei einer späteren Neuinstallation wiederverwenden kannst. Hake „Auch die MAKO-Renderer-Einstellungen des Spiels entfernen“ an, um sie ebenfalls zu löschen.

### 5. Vorhandene Einstellungen übernehmen

Hast du `mako-launch` bei einem Spiel schon früher von Hand eingetragen, zeigt dieses Spiel die Schaltfläche „Einstellungen übernehmen“. Ein Klick darauf legt das MAKO-Profil des Spiels an und bezieht es ab dann in die automatische Pfadaktualisierung ein.

### 6. Automatische Pfadaktualisierung nach Spiel-Updates

- Bei jedem erneuten Einlesen werden die ausführbaren Dateien der **über dieses Werkzeug installierten** Spiele neu erkannt. Hat ein Update die Datei verschoben oder umbenannt, werden die zugeordneten MAKO-Prozesse automatisch angepasst und die Änderung im Protokollbereich aufgeführt.
- Prozesse, die du in MAKO UI **von Hand hinzugefügt** hast, bleiben erhalten.
- Hast du das Profil eines Spiels in MAKO UI gelöscht, respektiert das Werkzeug das und legt es nicht neu an.
- Ist eine Bibliothek vorübergehend offline (zum Beispiel ein nicht angeschlossenes externes Laufwerk), bleiben die Einstellungen dieser Spiele unverändert.

### 7. Spiele direkt aus der Liste starten

Jede Zeile hat eine Schaltfläche „▶ Starten“, die das Spiel über Steam startet. Während das Spiel läuft, zeigt die Schaltfläche „Läuft“.

### 8. Live-Anzeige der tatsächlich aktiven MAKO-Funktionen

Die Spalte „Aktive MAKO-Funktionen“ wird alle 3 Sekunden aktualisiert. Sie zeigt, was MAKO im Spiel **tatsächlich angewendet** hat, nicht was in der Konfigurationsdatei steht:

- **Frame-Generierung**: fester Multiplikator (zum Beispiel ×2) oder adaptiver Modus (Ziel-FPS und maximaler Multiplikator), Flow-Skalierung und Leistungsmodus.
- **Skalierung**: Skalierungsverfahren und Auflösung (zum Beispiel 1280×720 → 2560×1440) sowie Supersampling.
- **Weitere Layer**: vkBasalt, Zink, ALSA-Audio.
- **Ausstehende Änderungen** wie „Spielneustart erforderlich“ oder „Swapchain-Neuaufbau erforderlich“ sowie Fehler, die MAKO meldet.

Ist bei einem Spiel Mako FG installiert, MAKO aber nicht wirklich geladen, wird auch das angezeigt, damit du dem Problem nachgehen kannst.

### 9. Overlay beim Spielstart

Ist der MAKO-Assistent geöffnet, während du ein Spiel startest, zeigt er die aktiven MAKO-Funktionen etwa 10 Sekunden lang unten rechts an, sobald er erkennt, dass MAKO im Spiel arbeitet, und blendet sie dann aus:

- Es erscheint einmal pro Start, übernimmt nie den Tastatur- oder Mausfokus, und Mausklicks gehen hindurch.
- Es kann über Proton-Spielen im Vollbild erscheinen.
- Hat ein Spiel mit installiertem Mako FG MAKO 90 Sekunden nach dem Start noch nicht geladen, erscheint stattdessen eine Warnung.
- Du kannst es mit dem Kontrollkästchen „Overlay beim Spielstart“ in der Werkzeugleiste ausschalten.

### 10. Suche und Filter

- Suche nach Spielname (in jeder Sprache) oder nach App-ID.
- Filter: alle Spiele, Mako FG installiert, Mako FG nicht installiert, nur MAKO-Einstellungen, läuft.

### 11. Zwölf Oberflächensprachen

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

Beim ersten Start richtet sich die Sprache nach deiner Systemsprache. Du kannst sie jederzeit oben rechts ändern; die Änderung gilt sofort und wird gespeichert.

### 12. Auf Sicherheit ausgelegt

- `conf.toml` und Steams `localconfig.vdf` werden vor jeder Änderung gesichert (`*.mako-assistant.bak`).
- Nach dem Schreiben prüft das Werkzeug `conf.toml` mit `mako-cli validate`. Lehnt MAKO die Datei ab, wird das Original automatisch wiederhergestellt.
- `localconfig.vdf` wird nie direkt bearbeitet, solange Steam läuft.
- Wenn du auf „Mako FG installieren“ klickst, prüft das Werkzeug zuerst, ob MAKO Renderer installiert ist (`~/.local/bin/mako-launch` vorhanden) und MAKO UI seine Einstellungen angelegt hat. Fehlt eines davon, wird nichts geändert, und du wirst aufgefordert, zuerst MAKO zu installieren.

## MAKO-Assistent installieren

**AppImage (empfohlen)**: Python und Qt sind enthalten, es muss nichts weiter installiert werden.

1. Lade `MAKO_Assistant-<Version>-x86_64.AppImage` von der [Releases](https://github.com/mosesmoon/mako-assistant/releases)-Seite herunter.
2. Mach die Datei ausführbar: Rechtsklick auf die Datei → Eigenschaften → Berechtigungen und „Datei als Programm ausführen“ aktivieren (die Bezeichnung hängt vom Dateimanager ab).
3. Doppelklicke sie, um den MAKO-Assistenten zu öffnen.

Oder im Terminal:

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

Startet sie nicht, fehlt deinem System eventuell FUSE; starte sie dann mit `./MAKO_Assistant-*-x86_64.AppImage --appimage-extract-and-run`.

**Aus dem Quellcode**: benötigt Python 3.11 oder neuer und PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # direkt starten
./install.sh        # nach ~/.local/share/mako-assistant installieren und einen Eintrag im Anwendungsmenü anlegen
```

## Bekannte Einschränkungen

- **Im Spielmodus des Steam Deck (gamescope) erscheint das Overlay nicht.** Verwende auf dem Steam Deck stattdessen das Decky-Plugin von MAKO.
- Spiele im exklusiven Vollbild unter nativem Wayland können das Overlay verdecken.
- Startoptionen lassen sich nur über den Steam-Client-Port live ändern, den Decky Loader öffnet (8080). Ohne Decky schließe Steam vor dem Übernehmen, oder lass das Werkzeug Steam schließen und neu starten.
- Die Anzeige der tatsächlich aktiven Funktionen und die MAKO-Profil-Metadaten werden im Format der aktuellen MAKO-Version gelesen. Nach einem großen MAKO- oder Steam-Update werden sie eventuell vorübergehend nicht angezeigt (du siehst „—“); Installieren und Entfernen funktionieren aber weiterhin.
- Auf Thailändisch, Vietnamesisch, Malaiisch und Hindi sind die Rechtsklickmenüs englisch (Qt hat für diese Sprachen keine offiziellen Übersetzungen). Steam hat keine malaiischen oder Hindi-Spielnamen, daher zeigen diese beiden Sprachen immer die Originalnamen.
- Es wird nur die jeweils letzte Sicherung aufbewahrt.

## Wo Daten gespeichert werden

| Ort | Inhalt |
|---|---|
| `~/.config/mako-assistant/state.json` | Eigener Zustand des MAKO-Assistenten: Spielelisten-Cache, über dieses Werkzeug installierte Spiele, Oberflächensprache, Overlay-Einstellung |
| `~/.config/mako-render/conf.toml` | Einstellungen von MAKO Renderer (Spielprofile) |
| `~/.config/mako-render/profile-metadata.json` | MAKO-Profil-Metadaten (Spielnamen, Steam-App-IDs) |
| `<Steam>/userdata/<Benutzer-ID>/config/localconfig.vdf` | Steam-Startoptionen |
