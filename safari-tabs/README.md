# safari-tabs

> **Lieber in der Claude-App?** Siehe [`claude-app/`](claude-app/README.md): Erweiterung installieren und einfach „Räum meine Safari-Tabs auf“ schreiben.

Räumt deine Safari-Tabs in zwei Schritten auf:

1. **Überblick & Empfehlung:** Du siehst alle offenen Tabs auf einen Blick: wie viele, welche Seiten am häufigsten, und welche Tabs du schließen kannst (mit Begründung).
2. **Schließen:** Nach deiner Bestätigung werden die empfohlenen Tabs geschlossen.
3. **Einsortieren:** Die übrigen Tabs kommen in deine **vorhandenen Lesezeichen-Ordner**. Das Tool schlägt für jeden Tab den passenden Ordner vor, du kannst jede Zuordnung ändern.

Nur Python-Standardbibliothek – läuft mit dem `python3`, das macOS mitbringt.

## Was zum Schließen empfohlen wird

| Regel | Beispiel |
|---|---|
| Leere Tabs / Startseite | `favorites://`, `about:blank` |
| Duplikate (auch mit `www.`, `m.`, Tracking-Parametern, YouTube-Zeitstempel) | zweimal dasselbe Video |
| Suchergebnisse | Google, Bing, DuckDuckGo, Ecosia, YouTube-/Amazon-Suche … |
| Login-/Anmeldeseiten | `accounts.google.com`, `/login`, `/oauth` … |
| Fehlerseiten | „404 Not Found“, „Safari kann die Seite nicht öffnen“ |
| Schon gespeichert | URL liegt schon in deinen Lesezeichen (das Tool zeigt, in welchem Ordner) |

**iPhone/iPad:** Ist Safari in iCloud eingeschaltet, werden die Tabs deiner anderen Geräte automatisch mit analysiert und einsortiert (die Lesezeichen erscheinen über iCloud überall). Schließen lassen sie sich nicht automatisch – dafür gibt das Tool eine Checkliste aus.

Web-Apps wie Gmail, Kalender, WhatsApp Web, Spotify und `localhost` bleiben offen und werden nicht gespeichert.

## Wie der passende Ordner gefunden wird

Für jeden Tab werden alle deine Lesezeichen-Ordner (inkl. Unterordner) bewertet. Die wichtigsten Hinweise sind:

1. **Art des Inhalts:** Das Tool erkennt, ob ein Tab ein Video, Buch, Artikel, Tool, Event, Forum, KI-Chat oder Shop ist (YouTube → Video, ChatGPT/Claude/Perplexity → KI-Chat, Reddit/Stack Overflow/GitHub-Issues → Forum, Goodreads/Thalia → Buch, Amazon/Zalando → Shop, Meetup/Eventim → Event, Nachrichtenseiten/Blogs → Artikel, GitHub/regex101/Online-Konverter → Tool). Ordner, die so heißen (auch auf Englisch: *Video, Book, Article, Tool, Event, Forum, AI-Chat, Shop*), werden automatisch erkannt.
1. **Gleiche Website:** Der Ordner enthält schon Lesezeichen von derselben Seite/Domain (stärkstes Signal).
2. **Stichwort:** Ein Wort aus dem Ordnernamen steht im Titel oder in der Adresse des Tabs (Ordner „Python“ ← „Sorting HOW TO — Python docs“).
3. **Thema:** Der Ordnername passt zum Thema der Seite (Ordner „Kochen“ ← chefkoch.de, „Reisen“ ← booking.com, „Dev“ ← github.com …).

Bei mehreren Treffern gewinnt der spezifischere Unterordner. Tabs ohne passenden Ordner bekommen keinen Vorschlag und werden nicht gespeichert, bis du sie zuordnest (z. B. `4>Video`). Es gibt keinen automatischen Sammelordner. Wer einen will, gibt ihn mit `--fallback NAME` an. Neue Ordner brauchen mindestens 2 Tabs und einen konkreten Namen (kein „Sonstiges“ o. Ä.). Die Leseliste wird ignoriert.

## Einrichtung (einmalig)

```bash
git clone https://github.com/babizeps/dev.git && cd dev/safari-tabs
```

- **Festplattenvollzugriff für Terminal** – nötig, damit das Tool deine Lesezeichen-Ordner sehen kann:
  Systemeinstellungen → Datenschutz & Sicherheit → Festplattenvollzugriff → Terminal aktivieren, Terminal neu starten.
- **Safari steuern:** Beim ersten Start fragt macOS, ob Terminal Safari steuern darf → **OK**.

## Benutzung

```bash
python3 safari_tabs.py --overview      # nur Überblick + Empfehlung, nichts ändern
python3 safari_tabs.py                 # Überblick, dann Schritt 1 (schließen) und Schritt 2 (einsortieren)
```

**Schritt 1 – schließen**
```
Enter / j    empfohlene Tabs schließen
n            nichts schließen, weiter zu Schritt 2
12b 5l 7s    Tab 12 behalten, 5 als Lesezeichen, 7 schließen   (3-6b = Bereich)
q            abbrechen
```

**Schritt 2 – einsortieren**
```
Enter / j    Lesezeichen wie vorgeschlagen eintragen
o            nummerierte Liste deiner Ordner anzeigen
4>12         Tab 4 in Ordner Nr. 12
4>Video/Musik  Tab 4 in neuen Unterordner „Musik“ im vorhandenen Ordner „Video“
4>Kochen     Tab 4 in Ordner „Kochen“ (Teilname reicht, sonst wird ein neuer Ordner angelegt)
4x           Tab 4 nicht speichern
q            abbrechen
```

Zum Eintragen beendet das Tool Safari kurz (sonst würde Safari die Änderung überschreiben), legt vorher eine Sicherung `~/Library/Safari/Bookmarks.plist.backup-…` an und öffnet Safari wieder. Falls Safari deine Tabs nicht selbst wiederherstellt, öffnet das Tool sie neu. Bereits vorhandene Lesezeichen werden nie doppelt eingetragen.

### Weitere Optionen

| Option | Zweck |
|---|---|
| `-y`, `--yes` | Empfehlung ohne Rückfragen umsetzen |
| `--close-saved` | eingeordnete Tabs danach auch schließen |
| `--fallback NAME` | Sammelordner für Tabs ohne Treffer (Standard: keiner) |
| `--report bericht.md` | Überblick als Markdown speichern |
| `--export datei.html` | zusätzlich eine Lesezeichen-HTML-Datei schreiben |
| `--config regeln.json` | eigene Regeln (siehe unten) |
| `--dump-config` | Standardregeln anzeigen |
| `--json` | Analyse als JSON ausgeben |
| `--nur-mac` | Tabs von iPhone/iPad (iCloud) nicht einbeziehen |
| `--sortieren ORDNER` | Ordner smart sortieren (Unterordner zuerst, dann nach Website/Titel) |
| `--auto-installieren` | Automatik einrichten (`--haeufigkeit monatlich/woechentlich/taeglich`, Standard monatlich; ordnet dabei auch alles in Unterordner, `--inaktiv-minuten 15`, `--gespeicherte-schliessen`) |
| `--auto-status` / `--auto-entfernen` | Automatik prüfen / ausschalten |
| `--auto -n` | Probelauf: zeigt, was die Automatik jetzt tun würde |
| `--rueckgaengig` | letzte Speicherung rückgängig machen (nur deren Lesezeichen) |
| `--sicherungen` | Sicherungen der Lesezeichen auflisten |
| `--wiederherstellen NAME` | eine Sicherung zurückspielen (aktueller Stand wird vorher gesichert) |

**Fehler korrigieren:** `python3 safari_tabs.py --rueckgaengig` macht die letzte Änderung rückgängig (Speicherung, Umstrukturierung oder Sortierung). `--sicherungen` und `--wiederherstellen NAME` spielen eine komplette Sicherung zurück. Was wann eingetragen wurde, steht in `~/.safari-tabs/verlauf.json`.

## Eigene Regeln

`python3 safari_tabs.py --dump-config > regeln.json`, anpassen, mit `--config regeln.json` starten. Nur geänderte Schlüssel sind nötig:

```json
{
  "fallback_folder": "Später lesen",
  "min_match_score": 4,
  "close_patterns": ["^https?://(www\\.)?bild\\.de/"],
  "bookmark_patterns": ["^https?://intranet\\.firma\\.de/"],
  "keep_open_patterns": ["^https?://app\\.todoist\\.com/"],
  "categories": { "Uni": ["moodle.uni-beispiel.de", "re:/vorlesung/"] }
}
```

## Tests (ohne Mac)

```bash
python3 -m unittest discover -s tests
python3 tests/make_sample_plist.py /tmp/B.plist
python3 safari_tabs.py --from-json tests/sample_tabs.json --bookmarks /tmp/B.plist
```
