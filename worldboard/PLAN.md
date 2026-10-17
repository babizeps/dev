# Worldboard – Plan

Eine persönliche Desktop-App für Worldbuilding und Moodboards, inspiriert von
Midjourney Patchwork und Milanote.

## Lean-MVP

1. **Leinwand** – unendliche Fläche, Zoomen und Verschieben
2. **Eine Karte für alles** – Titel, Text, Typ (Notiz, Figur, Ort, Fraktion, Ereignis, Gegenstand), optional ein Bild (Drag & Drop)
3. **Verbindungen** zwischen Karten (ohne Beschriftung)
4. **Auto-Speichern** und Löschen

Dazu: zwei Stile (Studio, Skizzenbuch), jeweils mit Tag- und Nachtmodus.

**Fertig, wenn:** eine kleine Welt mit Karten, Bildern und Verbindungen angelegt,
die App geschlossen und beim nächsten Start alles wieder da ist.

## Roadmap nach dem MVP

| Stufe | Ziel | Features |
|---|---|---|
| 1 Sicher | echten Welten vertrauen | Tauri-Hülle mit Datei-Speicher, Rückgängig/Wiederholen, Backup, Bild per Strg+V, Kartengröße ändern |
| 2 Ordnung | Überblick bei 100+ Karten | Suche, Filter nach Typ, beschriftete Verbindungen, Unter-Boards |
| 3 Worldbuilding | mehr als bunte Notizen | eigene Felder pro Typ, Detailansicht, `[[Verlinkungen]]`, Zufallsgenerator |
| 4 Moodboard | Inspiration sammeln | Link-Karten mit Vorschau, Farbpalette aus Bild, Vorlagen, PNG-Export |
| 5 KI | Assistenz | Karte ausfüllen, Bild generieren, „Frag deine Welt“ |
| 6 Handy | unterwegs | Sync über Supabase (neueste Änderung pro Datensatz gewinnt), schlanke Handy-App |

## Architektur

```
UI (React + React Flow)          src/ui/
Core (reines TypeScript)         src/core/     Typen, Operationen, Store, Migrationen
Storage-Adapter (Interface)      src/storage/  IndexedDB (MVP) → Tauri-Dateien → Sync
```

- Der **Core** kennt weder React noch Tauri. Jede Änderung läuft über eine Operation in
  `src/core/world.ts`, die `updatedAt` setzt.
- Der **Store** ist die Wahrheit, nicht React Flow. React Flow bekommt seine Knoten aus dem Store.
- **Löschen** setzt nur `deletedAt`, damit Löschungen später synchronisiert werden können.
- **Bilder** werden unter dem SHA-256 ihres Inhalts gespeichert: keine Duplikate, unveränderliche Dateien.
- **`schemaVersion`** plus `migrate()` erlauben spätere Formatänderungen. Eine unbekannte, neuere Version
  wird abgelehnt statt überschrieben.
- Reservierte Felder für die Roadmap: `boardId` (Unter-Boards), `fields` (eigene Felder), `label` (Beschriftungen).
