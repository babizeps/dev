---
name: archive-digest
description: Erstellt zu einer Artikel-URL die passenden archive.ph-Links (neuester Snapshot, alle Snapshots, jetzt archivieren), ohne die Seite abzurufen. Verwenden, wenn der Nutzer nach einem archive.ph- / archive.today-Link zu einem Artikel fragt oder eine Artikel-URL mit "archive", "Archiv-Link" o. ä. schickt.
---

# archive-digest

Der Nutzer will zu einem Artikel nur den archive.ph-Link. Du baust die Links aus der URL zusammen und gibst sie zurück.

**Ruf keine Seite ab**, weder den Artikel noch archive.ph. Du brauchst dafür kein Tool und keine Code-Ausführung, nur die URL aus der Nachricht.

## URL vorbereiten

1. Fehlt `https://`, ergänze es.
2. Entferne Tracking-Parameter (`utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`, `ref`, `cmp`, `wt_mc`) und einen `#`-Anker. Andere Parameter lässt du stehen.
3. Ist die URL schon ein archive.ph-/archive.today-Link (`archive.ph`, `archive.is`, `archive.today`, `archive.li`, `archive.vn`, `archive.md`, `archive.fo`), gib ihn einfach unverändert zurück.

## Antwort

Antworte kurz, ohne Einleitung und ohne Zusammenfassung des Artikels:

```
**Neuester Snapshot:** https://archive.ph/newest/<URL>
Alle Snapshots: https://archive.ph/<URL>
Noch nicht archiviert? Jetzt archivieren: https://archive.ph/?url=<URL>
```

Bei mehreren URLs: pro Artikel ein solcher Block mit der Domain bzw. dem Titel aus der URL als Überschrift.

Füge höchstens einen kurzen Hinweis an, wenn er nötig ist, z. B. dass archive.ph im Browser manchmal ein CAPTCHA zeigt oder dass es zu sehr neuen Artikeln noch keinen Snapshot geben kann.
