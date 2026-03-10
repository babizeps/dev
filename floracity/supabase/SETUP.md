# Supabase Setup

## 1. Projekt erstellen
1. Account auf https://supabase.com anlegen
2. Neues Projekt erstellen
3. Project URL und anon key in `.env` eintragen (siehe `.env.example`)

## 2. Datenbank-Schema anlegen
```sql
-- In Supabase SQL Editor ausführen:
-- (Datei: supabase/migrations/001_initial_schema.sql)
```
Oder mit Supabase CLI:
```bash
npx supabase db push
```

## 3. Storage Bucket
Im Supabase Dashboard unter Storage:
- Neuen Bucket namens `plant-photos` erstellen
- Bucket als **Public** setzen (für öffentliche Fotos)
- Policy: Authenticated users können uploaden

## 4. Edge Function deployen
```bash
npx supabase functions deploy identify-plant \
  --project-ref YOUR_PROJECT_REF
```

Secrets setzen:
```bash
npx supabase secrets set PLANT_ID_API_KEY=your_plant_id_key \
  --project-ref YOUR_PROJECT_REF
```

Plant.id API Key: https://plant.id (kostenloser Testplan verfügbar)

## 5. App starten
```bash
cp .env.example .env
# .env mit echten Werten befüllen

npx expo start
```
