# Safari-Tabs aufräumen – Erweiterung für die Claude-App (Mac)

Damit kannst du in der normalen Claude-App einfach schreiben **„Räum meine Safari-Tabs auf“**. Claude:

1. zeigt dir einen **Überblick** über alle offenen Tabs und eine **Empfehlung**, welche du schließen kannst (prüft die Vorschläge zusätzlich selbst),
2. schließt sie **nach deinem OK**,
3. schlägt für die übrigen Tabs deine **vorhandenen Lesezeichen-Ordner** vor (Video, Book, Article, Tool, Event, Forum, AI-Chat, Shop …) und trägt sie **nach deinem OK** ein.

Ohne deine Bestätigung wird nichts geschlossen oder gespeichert.

## Installation

1. Lade die Datei [`dist/safari-tabs.mcpb`](dist/safari-tabs.mcpb) herunter (auf GitHub: Datei öffnen → „Download raw file“).
2. Doppelklick auf die Datei → die Claude-App öffnet sich → **Installieren**.
   (Alternativ: Claude → Einstellungen → Erweiterungen → Datei hineinziehen.)
3. Zugriffsrechte für die App **Claude** (einmalig):
   - **Festplattenvollzugriff**: Systemeinstellungen → Datenschutz & Sicherheit → Festplattenvollzugriff → **Claude** einschalten → Claude neu starten.
     Nötig, damit Claude deine Lesezeichen-Ordner sehen und darin speichern kann.
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

## Für Entwickler

- `server.py` – MCP-Server (nur Python-Standardbibliothek), nutzt `../safari_tabs.py`
- `manifest.json` – Beschreibung der Erweiterung
- `python3 build.py` – baut `dist/safari-tabs.mcpb` neu
- Tests: `python3 -m unittest discover -s ../tests`
