# archive-digest – Skill für Claude

Ein Skill für die normale Claude-App (claude.ai, Desktop-App, Smartphone-App). Du schickst Claude im Chat einen Artikel-Link und bekommst einen Überblick: TL;DR, Kernaussagen, Fakten & Zahlen und eine kurze Einordnung.

archive.ph kommt **nur zum Einsatz, wenn der Artikel hinter einer Paywall steht**. Claude ruft zuerst das Original ab. Ist es frei lesbar, fasst Claude es direkt zusammen. Bricht der Text nach dem Anriss ab oder erscheinen Abo-Hinweise („SPIEGEL+“, „Z+“, „Subscribe to continue“ usw.), holt Claude den archivierten Volltext von archive.ph. Nennst du archive.ph selbst oder schickst einen archive.ph-Link, wird archive.ph immer verwendet.

## Einrichten (einmalig)

1. `archive-digest-skill.zip` herunterladen.
2. In Claude: **Einstellungen → Funktionen (Capabilities)**: **Code-Ausführung und Dateierstellung** einschalten (Skills brauchen das).
3. Unter **Skills** auf **Skill hochladen** klicken und die ZIP-Datei auswählen.
4. Prüfen, dass die **Websuche bzw. der Web-Abruf** aktiviert ist (im Chat über das Werkzeug-Menü).

## Benutzen

Einfach im Chat schreiben, zum Beispiel:

- `Fass mir den Artikel zusammen: https://www.zeitung.de/artikel.html`: Paywall-Prüfung, bei Bedarf archive.ph
- `Bitte kurz: https://www.zeitung.de/artikel.html`
- `Überblick auf Englisch: https://archive.ph/AbCd1`: archive.ph-Link, wird direkt verwendet
- mehrere Links auf einmal: jeder wird einzeln geprüft, danach vergleicht Claude die Artikel

## Wenn archive.ph blockiert

archive.ph zeigt automatischen Abrufen manchmal ein CAPTCHA. Claude sagt dir dann Bescheid. Zwei Auswege:

- Den Link im Browser öffnen, die Seite speichern (Strg+S, „Webseite, nur HTML“) und die Datei in den Chat ziehen. Claude holt den Text mit dem beiliegenden Skript heraus.
- Den Artikeltext einfach in den Chat kopieren.

## Inhalt

```
skill/archive-digest/
├── SKILL.md                    Anleitung für Claude (Paywall-Prüfung, Abruf, Format)
└── scripts/extract_article.py  holt den Text aus einer gespeicherten archive.ph-Seite
```

Nach Änderungen die ZIP-Datei neu bauen:

```bash
cd skill && zip -r ../archive-digest-skill.zip archive-digest -x '*__pycache__*'
```
