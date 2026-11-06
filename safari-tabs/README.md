# safari-tabs

Räumt deine Safari-Tabs auf: analysiert alle offenen Tabs, **schließt unnötige** und **sichert die wichtigen geordnet nach Kategorien als Lesezeichen**.

Nur Python-Standardbibliothek – läuft mit dem `python3`, das macOS mitbringt.

## Was als „unnötig“ gilt

| Regel | Beispiel |
|---|---|
| Leere Tabs / Startseite | `favorites://`, `about:blank` |
| Duplikate (auch mit `www.`, `m.`, Tracking-Parametern, YouTube-Zeitstempel) | zweimal dasselbe Video |
| Suchergebnisse | Google, Bing, DuckDuckGo, Ecosia, YouTube-/Amazon-Suche … |
| Login-/Anmeldeseiten | `accounts.google.com`, `/login`, `/oauth` … |
| Fehlerseiten | „404 Not Found“, „Safari kann die Seite nicht öffnen“ |
| Bereits gespeichert | URL ist schon in deinen Lesezeichen |

Web-Apps wie Gmail, Kalender, WhatsApp Web, Spotify, `localhost` bleiben **offen** und werden nicht gespeichert.
Alles andere wird als Lesezeichen gesichert, in den Ordner **Tab-Archiv** mit Unterordnern wie *Entwicklung, Videos, Nachrichten, Social, Shopping, Wissen & Lernen, Arbeit & Dokumente, Reisen & Orte, Rezepte, Finanzen, Sonstiges*.

## Installation

```bash
git clone https://github.com/babizeps/dev.git && cd dev/safari-tabs
```

Beim ersten Start fragt macOS, ob Terminal Safari steuern darf → **OK**
(sonst: Systemeinstellungen → Datenschutz & Sicherheit → Automation → Terminal → Safari).

Damit bereits gespeicherte Lesezeichen erkannt werden und für `--direct`:
Systemeinstellungen → Datenschutz & Sicherheit → **Festplattenvollzugriff** → Terminal aktivieren.

## Benutzung

```bash
python3 safari_tabs.py --dry-run          # nur anzeigen, nichts ändern
python3 safari_tabs.py                    # anzeigen, korrigieren, dann ausführen
python3 safari_tabs.py --direct           # Lesezeichen direkt in Safari eintragen
python3 safari_tabs.py --direct --close-saved   # gesicherte Tabs danach auch schließen
```

Nach der Analyse siehst du eine nummerierte Liste und kannst vor dem Ausführen korrigieren:

```
> 3s 7l 12b      # 3 schließen, 7 als Lesezeichen, 12 behalten
> 5-9s           # 5 bis 9 schließen
> k 4 Videos     # Tab 4 in Kategorie „Videos“
> (Enter)        # ausführen      q = abbrechen
```

### Wie die Lesezeichen in Safari landen

- **Standard:** Es wird eine HTML-Datei in `~/Downloads` erzeugt. In Safari: *Ablage → Importieren von → Lesezeichen-HTML-Datei…*
- **`--direct`:** Das Tool beendet Safari kurz, trägt die Lesezeichen in `~/Library/Safari/Bookmarks.plist` ein (vorher wird eine Sicherung `Bookmarks.plist.backup-…` angelegt) und startet Safari wieder. Falls Safari deine restlichen Tabs nicht wiederherstellt, öffnet das Tool sie neu. Doppelte Lesezeichen werden übersprungen, mehrere Läufe ergänzen denselben Ordner.
  Hinweis: Mit iCloud-Lesezeichen-Sync funktioniert das normalerweise, die HTML-Datei bleibt aber immer als Backup erhalten.

### Weitere Optionen

| Option | Zweck |
|---|---|
| `-y`, `--yes` | ohne Rückfrage ausführen |
| `--folder NAME` | anderer Ordnername als „Tab-Archiv“ |
| `--report bericht.md` | Markdown-Bericht mit allen Tabs schreiben |
| `--export datei.html` | Speicherort der HTML-Datei |
| `--config regeln.json` | eigene Regeln (siehe unten) |
| `--dump-config` | Standardregeln anzeigen |
| `--json` | Analyse als JSON ausgeben |
| `--from-json tabs.json` | Tabs aus Datei lesen (zum Testen ohne Safari) |

## Eigene Regeln

`python3 safari_tabs.py --dump-config > regeln.json`, anpassen, dann mit `--config regeln.json` starten. Es reicht, nur die geänderten Schlüssel anzugeben:

```json
{
  "folder": "Leseliste",
  "close_patterns": ["^https?://(www\\.)?bild\\.de/"],
  "bookmark_patterns": ["^https?://intranet\\.firma\\.de/"],
  "keep_open_patterns": ["^https?://app\\.todoist\\.com/"],
  "categories": {
    "Uni": ["moodle.uni-beispiel.de", "re:/vorlesung/"]
  }
}
```

Kategorien: Domain (passt auch auf Subdomains), `domain/pfad` oder `re:` + regulärer Ausdruck. Eigene Kategorien haben Vorrang vor den Standardkategorien.

## Tests

```bash
python3 -m unittest discover -s tests
```
