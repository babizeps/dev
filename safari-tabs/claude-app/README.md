# Safari-Tabs aufräumen – Erweiterung für die Claude-App (Mac)

Damit kannst du in der normalen Claude-App einfach schreiben **„Räum meine Safari-Tabs auf“**. Claude:

1. zeigt dir einen **Überblick** über alle offenen Tabs und eine **Empfehlung**, welche du schließen kannst (prüft die Vorschläge zusätzlich selbst),
2. schließt sie **nach deinem OK**,
3. schlägt für die übrigen Tabs deine **vorhandenen Lesezeichen-Ordner** vor (Video, Book, Article, Tool, Event, Forum, AI-Chat, Shop …) und trägt sie **nach deinem OK** ein.

Ohne deine Bestätigung wird nichts geschlossen oder gespeichert.

## iPhone & iPad

Ist Safari auf deinen Geräten in iCloud eingeschaltet (iPhone: Einstellungen → [dein Name] → iCloud → Safari), liest Claude auf dem Mac auch die Tabs von iPhone und iPad mit:

- Sie erscheinen im Überblick mit dem Gerätenamen; Tabs, die auch am Mac offen sind, werden als doppelt erkannt.
- **Einsortieren** funktioniert genauso – über iCloud sind die Lesezeichen danach auch auf dem iPhone.
- **Schließen** geht auf dem iPhone nicht automatisch (Apple erlaubt das nicht). Du bekommst eine Checkliste und schließt die Tabs am iPhone (Tab-Übersicht → nach links wischen) oder am Mac in der Tab-Übersicht unter dem Gerät.
- Tipp: iPhone → Einstellungen → Apps → Safari → **Tabs schließen** → „Nach einer Woche“.

Die iPhone-Tabs sind so aktuell wie die letzte iCloud-Synchronisierung (kurz Safari auf dem iPhone öffnen hilft).

## Installation

1. Lade die Datei [`dist/safari-tabs.mcpb`](dist/safari-tabs.mcpb) herunter (auf GitHub: Datei öffnen → „Download raw file“).
2. Doppelklick auf die Datei → die Claude-App öffnet sich → **Installieren**.
   (Alternativ: Claude → Einstellungen → Erweiterungen → Datei hineinziehen.)
3. Zugriffsrechte für die App **Claude** (einmalig):
   - **Festplattenvollzugriff für Terminal**: Systemeinstellungen → Datenschutz & Sicherheit → Festplattenvollzugriff → **Terminal** einschalten (falls nicht in der Liste: **+** → Programme → Dienstprogramme → Terminal).
     Warum Terminal? Die Erweiterung bekommt in der Claude-App oft keinen Festplattenvollzugriff, selbst wenn „Claude“ freigegeben ist. Sie lässt die Lesezeichen deshalb über ein kurz geöffnetes Terminal-Fenster lesen und eintragen. Das Fenster kannst du danach schließen. Hat die Erweiterung selbst Zugriff, wird Terminal nicht gebraucht.
   - **Safari steuern**: Beim ersten Benutzen fragt macOS „Claude möchte Safari steuern“ → **OK**.
     (Falls verpasst: Datenschutz & Sicherheit → Automation → Claude → Safari.)

Falls macOS beim ersten Start fragt, ob die Entwicklerwerkzeuge installiert werden sollen: bestätigen – damit kommt `python3` auf den Mac.

## Benutzung

- Neuen Chat öffnen und schreiben: **„Räum meine Safari-Tabs auf“**
- oder über **+** → *Safari-Tabs aufräumen* → **tabs-aufraeumen** den fertigen Befehl einfügen.

Beim Speichern wird Safari kurz beendet und wieder geöffnet (sonst überschreibt Safari die Änderung). Vorher wird eine Sicherung `~/Library/Safari/Bookmarks.plist.backup-…` angelegt; deine offenen Tabs werden notfalls wieder geöffnet.

## Ohne .mcpb (manuell)

In `~/Library/Application Support/Claude/claude_desktop_config.json` eintragen (Pfad anpassen) und Claude neu starten:

```json
{
  "mcpServers": {
    "safari-tabs": {
      "command": "/usr/bin/python3",
      "args": ["/Users/DEINNAME/dev/safari-tabs/claude-app/server.py"]
    }
  }
}
```

## Unterordner – verschachtelt und smart sortiert

Schreib „Mach passende Unterordner für meine Tabs“ oder „Räum meinen Ordner Video auf“, oder nimm den Befehl **unterordner-erstellen**. Claude entwirft für jeden Ordner eine Struktur mit bis zu drei Ebenen, für die neuen Tabs **und** die Lesezeichen, die schon im Ordner liegen:

```
Video
├─ Musik (12)
│  ├─ Jazz (4)
│  └─ Lofi (5)
├─ Programmieren (7)
└─ (2 Einzelstücke direkt in Video)
```

Feste Regeln, die das Tool selbst prüft:

- **Von breit zu spezifisch:** Oben stehen breite Themen, darunter feinere. Ein Ordner, der nur aus genau einem Unterordner besteht, wird nicht angelegt. Höchstens drei Ebenen.
- **Mindestens 2 Einträge** in jedem neuen oder neu befüllten Ordner (Unterordner zählen mit).
- **Keine Sammelnamen** wie „Sonstiges“, „Misc“, „Allgemein“, „Diverses“, „Andere“, „Neu“. Einzelstücke bleiben direkt im übergeordneten Ordner.

Verletzt ein Vorschlag eine Regel, wird **nichts geändert**. Claude bessert den Baum nach und fragt dich erneut.

- Vorhandene Unterordner werden wiederverwendet.
- Du kannst den Vorschlag im Chat ändern (umbenennen, zusammenlegen, Ebenen streichen). Angewendet wird erst nach deinem OK.
- Unterordner, die durch das Umsortieren leer werden, verschwinden. Leere Ordner, die du selbst angelegt hast, bleiben.
- **Sortiert:** Unterordner zuerst und alphabetisch (Sammelordner, die du schon hast, ganz unten), dann die Lesezeichen nach Website und Titel. „Sortier meinen Ordner Article“ geht auch einzeln.
- **„Mach das rückgängig“** setzt den ganzen Ordner auf den Stand davor zurück. Hast du den Ordner inzwischen selbst geändert, fragt Claude vorher nach.

## Fehler korrigieren

Ist etwas im falschen Ordner gelandet, schreib z. B. „Die letzten Lesezeichen waren falsch, mach das rückgängig“ oder „Entferne ‚The AI Future Is for Everyone – WSJ‘ aus Article“ – oder nimm den Befehl **lesezeichen-korrigieren**. Claude kann jetzt:

- **Verlauf zeigen**: was wann in welchen Ordner eingetragen wurde, plus alle Sicherungen,
- **gezielt entfernen**: einzelne Lesezeichen (per Titel + Ordner, URL oder aus dem Verlauf). Deine Ordner und anderen Lesezeichen bleiben unangetastet,
- **letzte Speicherung rückgängig machen**: genau die Lesezeichen dieser Speicherung (und dabei neu angelegte, leere Ordner),
- **Sicherung zurückspielen**: nur wenn nötig. Der aktuelle Stand wird vorher selbst gesichert, damit auch das rückgängig gemacht werden kann.

Vor jedem Entfernen zeigt Claude dir die Liste und wartet auf dein OK. Ist Safari in iCloud eingeschaltet, kann iCloud gelöschte Einträge in seltenen Fällen zurückbringen. Claude prüft das kurz danach, notfalls löschst du sie mit ⌥⌘B in Safari.

## Probleme?

- **„Terminal hat keinen Festplattenvollzugriff“**: Schalter für Terminal einschalten, Terminal mit ⌘Q beenden, in Claude „weiter“ schreiben.
- **„Prüf den Zugriff“** in Claude zeigt, was die Erweiterung lesen darf und von welchem Programm sie gestartet wurde.
- Austauschdateien liegen kurz in `~/.safari-tabs/` und werden danach wieder gelöscht.

## Für Entwickler

- `server.py` – MCP-Server (nur Python-Standardbibliothek), nutzt `../safari_tabs.py`
- `manifest.json` – Beschreibung der Erweiterung
- `python3 build.py` – baut `dist/safari-tabs.mcpb` neu
- Tests: `python3 -m unittest discover -s ../tests`
- iPhone-Tabs kommen aus `~/Library/Containers/com.apple.Safari/Data/Library/Safari/CloudTabs.db` (nur lesend, über eine Kopie)
