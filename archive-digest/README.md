# archive-digest

Ruft Artikel über **archive.ph** (archive.today) ab und lässt Claude einen kompakten Überblick erstellen: TL;DR, Kernaussagen, Fakten & Zahlen und eine kurze Einordnung.

## Installation

```bash
cd archive-digest
pip install -r requirements.txt
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

## Verwendung

```bash
# archive.ph-Link direkt
archive-digest https://archive.ph/AbCd1

# Original-URL -> neuester Snapshot auf archive.ph
archive-digest https://www.example.com/artikel.html

# Kurzfassung (TL;DR + max. 5 Stichpunkte)
archive-digest -k https://archive.ph/AbCd1

# Überblick auf Englisch
archive-digest -l Englisch https://archive.ph/AbCd1

# Nur den extrahierten Artikeltext anzeigen (ohne Claude)
archive-digest --text https://archive.ph/AbCd1

# Lokal gespeicherte Seite verwenden (z.B. wenn archive.ph ein CAPTCHA zeigt)
archive-digest --html gespeichert.html
```

Weitere Optionen: `--model`, `--effort low|medium|high|xhigh|max`, `--mirror https://archive.is`.

## Hinweise

- archive.ph zeigt automatisierten Anfragen manchmal ein CAPTCHA. Dann öffnest du den Link im Browser, speicherst die Seite (Strg+S, „nur HTML“) und übergibst sie mit `--html`.
- Gibt es noch keinen Snapshot, meldet das Tool einen Link zum Archivieren.
- Standardmodell ist `claude-opus-5-5`. Lehnt das Modell eine Anfrage ab, springt die serverseitige Fallback-Funktion (`fallbacks: "default"`) automatisch ein.

## Tests

```bash
pip install pytest
python -m pytest tests
```
