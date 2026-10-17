# Worldboard

Eine persönliche Leinwand für Worldbuilding und Moodboards: Figuren, Orte, Fraktionen,
Ereignisse, Gegenstände und Notizen als Karten anlegen, Bilder hineinziehen und alles
miteinander verbinden. Plan, Roadmap und Architektur stehen in [PLAN.md](PLAN.md).

| Studio · Tag | Studio · Nacht |
|---|---|
| ![Studio, Tagmodus](docs/studio-light.png) | ![Studio, Nachtmodus](docs/studio-dark.png) |
| **Skizze · Tag** | **Skizze · Nacht** |
| ![Skizzenbuch, Tagmodus](docs/sketch-light.png) | ![Skizzenbuch, Nachtmodus](docs/sketch-dark.png) |

## Starten

Voraussetzung: [Node.js](https://nodejs.org) 20 oder neuer.

```bash
cd worldboard
npm install
npm run dev
```

Dann <http://localhost:1420> im Browser öffnen.

## Bedienung

| Aktion | So geht's |
|---|---|
| Neue Karte | Doppelklick auf die Leinwand oder Typ oben in der Leiste wählen |
| Kartentyp ändern | Auf die Typ-Plakette in der Karte klicken |
| Bild hinzufügen | Bilddatei auf eine Karte ziehen (oder auf die Leinwand für eine neue Karte) |
| Verbinden | Punkt rechts an der Karte auf eine andere Karte ziehen |
| Löschen | Karte oder Linie anklicken, dann Entf |
| Stil und Modus | Oben rechts: Studio/Skizze und Sonne/Mond |

Alles wird automatisch gespeichert.

> **Hinweis zum MVP:** Die Daten liegen im Speicher des Browsers (IndexedDB) und gehören
> zu genau diesem Browser und dieser Adresse. Löschst du die Website-Daten, ist die Welt weg.
> Für echte Welten kommt als nächster Schritt die Desktop-Hülle mit Tauri, die in eine Datei speichert
> (Roadmap Stufe 1).

## Entwickeln

```bash
npm test            # Unit-Tests für Core und Speicher (Vitest)
npm run test:e2e    # Browser-Tests (Playwright), startet den Dev-Server selbst
npm run build       # Typprüfung und Produktions-Build

SCREENSHOTS=1 npm run test:e2e -- screenshots   # Screenshots in docs/ neu erzeugen
```
