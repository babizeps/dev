# archive-digest – Skill für Claude

Ein Skill für die normale Claude-App (claude.ai, Desktop-App, Smartphone-App). Du schickst Claude im Chat einen archive.ph-Link, und Claude ruft den Artikel ab und gibt dir einen Überblick: TL;DR, Kernaussagen, Fakten & Zahlen und eine kurze Einordnung.

## Einrichten (einmalig)

1. `archive-digest-skill.zip` herunterladen.
2. In Claude: **Einstellungen → Funktionen (Capabilities)**: **Code-Ausführung und Dateierstellung** einschalten (Skills brauchen das).
3. Unter **Skills** auf **Skill hochladen** klicken und die ZIP-Datei auswählen.
4. Prüfen, dass die **Websuche bzw. der Web-Abruf** aktiviert ist (im Chat über das Werkzeug-Menü).

## Benutzen

Einfach im Chat schreiben, zum Beispiel:

- `Fass mir den Artikel zusammen: https://archive.ph/AbCd1`
- `https://www.zeitung.de/artikel.html über archive.ph, bitte kurz`: nimmt den neuesten Snapshot
- `Überblick auf Englisch: https://archive.ph/AbCd1`
- mehrere Links auf einmal: Claude fasst jeden Artikel zusammen und vergleicht sie danach

## Wenn archive.ph blockiert

archive.ph zeigt automatischen Abrufen manchmal ein CAPTCHA. Claude sagt dir dann Bescheid. Zwei Auswege:

- Den Link im Browser öffnen, die Seite speichern (Strg+S, „Webseite, nur HTML“) und die Datei in den Chat ziehen. Claude holt den Text mit dem beiliegenden Skript heraus.
- Den Artikeltext einfach in den Chat kopieren.

## Inhalt

```
skill/archive-digest/
├── SKILL.md                    Anleitung für Claude (Abruf, Format des Überblicks)
└── scripts/extract_article.py  holt den Text aus einer gespeicherten archive.ph-Seite
```

Nach Änderungen die ZIP-Datei neu bauen:

```bash
cd skill && zip -r ../archive-digest-skill.zip archive-digest -x '*__pycache__*'
```
