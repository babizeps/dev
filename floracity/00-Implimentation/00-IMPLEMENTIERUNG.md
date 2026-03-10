# FloraCity — Implementierungsplan

Eine spielerische Pokédex-App für die Flora von Forest City, Malaysia.
Nutzer fotografieren Pflanzen → KI identifiziert sie → Community-Datenbank wächst organisch.

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Framework | Expo (Expo Router, file-based routing) |
| Sprache | TypeScript |
| Kamera | `expo-camera` |
| Pflanzen-KI | Plant.id API v3 (via Supabase Edge Function) |
| Datenbank | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| Realtime | Supabase Channels (Leaderboard) |
| Foto-Storage | Supabase Storage (`plant-photos` Bucket) |
| State | Zustand |
| Animationen | React Native Reanimated v3 |
| Navigation | Expo Router |
| Secure Storage | `expo-secure-store` (JWT-Tokens) |

---

## Kern-Mechanik: Discovery Flow

```
Foto aufnehmen
     ↓
Plant.id API (via Edge Function)
     ↓
Konfidenz ≥ 90% → Auto-akzeptieren
Konfidenz 60–90% → Top-3 Vorschläge zur Auswahl
Konfidenz < 60%  → Warnung, Abbruch
     ↓
Supabase: Pflanze bereits bekannt?
  JA  → Discovery für User speichern (+25 XP)
  NEIN → Neue Pflanze anlegen + Pioneer! (+50 XP + Badge)
     ↓
User hat Art bereits? → kein XP (Duplicate)
```

---

## Gamification

### XP & Level
| Event | XP |
|---|---|
| Neue Art für User | 25 XP |
| Erste Entdeckung weltweit (Pioneer) | 50 XP + ⭐ Badge |
| Täglicher erster Fund | +5 XP Bonus |

**Level-Titel:** Seedling → Sprout → Sapling → Tree → Forest Guardian → Rainforest Elder → Ancient One → Legend

### Achievements
- First Bloom — erste Pflanze entdeckt
- Pioneer — weltweit erster Fund einer Art
- Collector — 10 Arten gesammelt
- Botanist — 25 Arten gesammelt
- Daily Explorer — 5 Tage in Folge
- National Pride — Hibiscus rosa-sinensis entdeckt
- Mangrove Walker — 5 Mangroven-Arten
- Cartographer — Fund an 3 verschiedenen GPS-Positionen

---

## Datenbankschema (Supabase)

```sql
plants       — Community-Pflanzendatenbank (wächst durch Funde)
profiles     — Nutzerprofile mit XP, Level, Pioneer-Count
discoveries  — Einzelne Funde (user_id + plant_id, UNIQUE)
achievements — Freigeschaltete Achievements pro User
leaderboard  — View: profiles + discovery count
```

Migration: `supabase/migrations/001_initial_schema.sql`

---

## Projektstruktur

```
floracity/
├── app/
│   ├── _layout.tsx              ✅ Root-Layout, Auth-Guard, Session-Laden
│   ├── (tabs)/
│   │   ├── _layout.tsx          ✅ Tab-Navigation (4 Tabs)
│   │   ├── index.tsx            ✅ Floradex — Community-Grid
│   │   ├── camera.tsx           ✅ Kamera + Discovery Flow
│   │   ├── leaderboard.tsx      ✅ Realtime-Rangliste
│   │   └── profile.tsx          ✅ Profil, Level, Achievements
│   ├── plant/[id].tsx           ✅ Pflanzen-Detailseite
│   └── auth/
│       ├── login.tsx            ✅ Login
│       └── signup.tsx           ✅ Registrierung
├── src/
│   ├── supabase/
│   │   ├── client.ts            ✅ Supabase-Client mit SecureStore
│   │   ├── plants.ts            ✅ plants-Tabelle CRUD
│   │   ├── discoveries.ts       ✅ Funde-Abfragen
│   │   └── leaderboard.ts       ✅ Leaderboard + Realtime-Subscription
│   ├── store/
│   │   ├── gameStore.ts         ✅ Zustand: XP, Level, Pioneer, Sammlung
│   │   └── authStore.ts         ✅ Zustand: Session/User
│   ├── components/
│   │   ├── PlantCard.tsx        ✅ Pokédex-Karte (gesperrt/frei/Pioneer)
│   │   └── XPPopup.tsx          ✅ Animiertes XP-Popup (Reanimated)
│   └── constants/
│       ├── colors.ts            ✅ Dunkles Grün-Theme
│       └── achievements.ts      ✅ Achievement-Definitionen
├── supabase/
│   ├── functions/
│   │   └── identify-plant/
│   │       └── index.ts         ✅ Edge Function: Plant.id → DB → XP
│   ├── migrations/
│   │   └── 001_initial_schema.sql ✅ Vollständiges Schema + RLS Policies
│   └── SETUP.md                 ✅ Setup-Anleitung
├── .env.example                 ✅
├── app.json                     ✅ Kamera + Location Permissions
└── tsconfig.json                ✅ Deno-Functions ausgeschlossen
```

---

## Implementierungs-Status

### Phase 1 — Foundation ✅
- [x] Expo-Projekt mit TypeScript angelegt
- [x] Expo Router konfiguriert (file-based routing)
- [x] Alle Dependencies installiert
- [x] Supabase-Schema entworfen (plants, profiles, discoveries, achievements, leaderboard view)
- [x] RLS Policies für alle Tabellen
- [x] Auth-Flow: Login + Signup + Auto-Profil-Erstellung (DB-Trigger)
- [x] Supabase-Client mit SecureStore-Token-Persistenz

### Phase 2 — Core Discovery ✅
- [x] Kamera-Screen mit Scan-Animation (Reanimated)
- [x] Foto aufnehmen + Base64 an Edge Function senden
- [x] Plant.id API v3 Integration (serverseitig, API-Key sicher)
- [x] Konfidenz-Modal (Top-3 Vorschläge bei 60–90% Konfidenz)
- [x] Pioneer-Logik: erste Entdeckung = doppelte XP + Flag
- [x] Foto-Upload zu Supabase Storage
- [x] GPS-Koordinaten-Logging
- [x] Floradex-Screen: Community-Grid mit Filter (Alle / Meine / Undiscovered)
- [x] Pflanzen-Detail: Community-Fotos, Pioneer-Banner, Statistiken

### Phase 3 — Gamification ✅
- [x] XP-System mit Level-Schwellen (exponentiell)
- [x] Level-Titel (Seedling → Legend)
- [x] Pioneer-Bonus (+50 XP, goldener Rahmen auf Karte)
- [x] XP-Popup-Animation (Reanimated, schwebt nach oben)
- [x] Achievement-Definitionen (8 Achievements)
- [x] Achievement-Anzeige im Profil (gesperrt/freigeschaltet)
- [x] XP-Fortschrittsbalken im Floradex + Profil

### Phase 4 — Social & Polish ✅
- [x] Leaderboard mit Realtime-Updates (Supabase Channels)
- [x] Eigene Zeile im Leaderboard hervorgehoben
- [x] Profil-Screen mit Stats (Arten, Pionier-Funde, XP)
- [x] Sign-Out mit Bestätigung
- [x] iOS/Android Kamera- & Location-Permissions konfiguriert
- [x] Dunkles Grün-Theme (Pokédex-inspiriert)

---

## Offen / Nächste Schritte

### Setup (einmalig)
- [ ] Supabase-Projekt anlegen + `.env` befüllen
- [ ] SQL-Migration ausführen
- [ ] Storage Bucket `plant-photos` anlegen (Public)
- [ ] Edge Function deployen: `npx supabase functions deploy identify-plant`
- [ ] Plant.id API Key als Secret setzen

### Verbesserungen (zukünftig)
- [ ] Achievement-Unlock-Animation (Lottie)
- [ ] Push-Notifications bei neuen Community-Funden
- [ ] Karte mit GPS-Pins aller Fundorte
- [ ] Streak-Tracking (täglicher Bonus)
- [ ] App-Icon + Splash Screen (Pokédex-Design)
- [ ] `eas build` für Testflight / Play Store

---

## Starten

```bash
cd floracity
cp .env.example .env
# .env mit Supabase-Werten befüllen

npx expo start
```

Vollständige Setup-Anleitung: [supabase/SETUP.md](supabase/SETUP.md)
