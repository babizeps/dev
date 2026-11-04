# archive-digest – Skill für Claude

Ein Skill für die Claude-App (claude.ai, Desktop, Smartphone). Du schickst Claude eine Artikel-URL und bekommst den passenden **archive.ph-Link** zurück. Claude ruft dabei keine Seite ab, es baut nur die Links zusammen.

Beispiel:

```
archive: https://www.example.com/politik/artikel-123.html?utm_source=newsletter
```

Antwort:

```
Neuester Snapshot: https://archive.ph/newest/https://www.example.com/politik/artikel-123.html
Alle Snapshots: https://archive.ph/https://www.example.com/politik/artikel-123.html
Noch nicht archiviert? Jetzt archivieren: https://archive.ph/?url=https://www.example.com/politik/artikel-123.html
```

Tracking-Parameter wie `utm_source` entfernt Claude dabei automatisch.

## Einrichten (einmalig)

1. `archive-digest-skill.zip` herunterladen.
2. In der Claude-App: **Einstellungen → Anpassungen → Skills**, dann **„+“ → „Skill erstellen“ → „Skill hochladen“** und die ZIP-Datei wählen.
3. Prüfen, dass der Schalter neben „archive-digest“ eingeschaltet ist.

Websuche und Code-Ausführung braucht dieser Skill nicht.

## Ohne Claude: Lesezeichen (Bookmarklet)

Noch schneller geht es mit einem Lesezeichen im Browser. Leg ein neues Lesezeichen an und trag als Adresse ein:

```
javascript:location.href='https://archive.ph/newest/'+location.href.split('#')[0]
```

Auf einer Artikelseite klickst du das Lesezeichen an und landest direkt beim neuesten archive.ph-Snapshot.

## ZIP neu bauen

```bash
cd skill && zip -r ../archive-digest-skill.zip archive-digest
```
