# Notion Clone — Implementierungsplan

## Übersicht
Open-Source-Reimplementierung von Notion als MVP.
Stack: Node.js + TypeScript, Fastify, Prisma, PostgreSQL, React + Vite, Tiptap.

---

## Status

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| 1 | Infrastruktur — Verzeichnisse, Docker, .env | ✅ Fertig |
| 2 | Backend Grundstruktur — package.json, tsconfig, Prisma, db, config, app | ✅ Fertig |
| 3 | Backend Auth — Lucia v3, Session-Cookies, register/login/logout/me | ✅ Fertig |
| 4 | Backend API — Workspaces + Blocks CRUD + Fractional Indexing | ✅ Fertig |
| 5 | Frontend Scaffold — Vite, tsconfig, package.json, index.html | ✅ Fertig |
| 6 | Frontend Types, API-Client, Stores (Zustand), Router | ✅ Fertig |
| 7 | Auth UI — Login/Register Forms + AuthPage | ✅ Fertig |
| 8 | Sidebar + Navigation — rekursive Seitenstruktur, SidebarItem | ✅ Fertig |
| 9 | Block Editor — Tiptap, PageView, PageTitle, Auto-Save (600ms debounce) | ✅ Fertig |
| 10 | Slash Command Extension — /‑Menü für Block-Typ-Wechsel | ✅ Fertig |
| 11 | Setup — npm install, PostgreSQL, Prisma Migration | ✅ Fertig |

**Aktueller Stand: MVP vollständig implementiert und lauffähig.**

---

## Architektur

```
notion-clone/
├── PLAN.md                   Dieser Plan
├── docker-compose.yml        Für Production-Deployment
├── backend/                  Node.js + Fastify + Prisma
│   ├── prisma/schema.prisma  Datenmodell (User, Session, Workspace, Block)
│   ├── prisma/migrations/    Generierte SQL-Migrations
│   └── src/
│       ├── auth/             Lucia v3 Session-Auth
│       ├── blocks/           Block CRUD + Fractional Indexing
│       ├── workspaces/       Workspace CRUD
│       └── plugins/          CORS, Cookie, Sensible
└── frontend/                 React + Vite + Tiptap
    └── src/
        ├── api/              Fetch-Wrapper + Endpunkte
        ├── store/            Zustand Stores (auth, blocks, ui)
        ├── components/
        │   ├── layout/       AppLayout, Sidebar, SidebarItem (rekursiv)
        │   ├── editor/       BlockEditor + BubbleMenu + SlashCommand
        │   ├── page/         PageView, PageTitle
        │   └── auth/         LoginForm, RegisterForm
        └── pages/            AuthPage, WorkspacePage, PageDetailPage
```

---

## Datenmodell (Kern)

```
Block {
  id          UUID
  type        page | paragraph | heading1-3 | bulleted_list |
              numbered_list | todo | code | divider | image
  workspaceId UUID → Workspace
  parentId    UUID? → Block (self-referential, für Seiten-Hierarchie)
  content     JSON  (tiptapDoc für page-Blöcke, title für Seiten)
  order       Float (Fractional Indexing, kein Renumbering nötig)
}
```

---

## API-Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/auth/register` | Registrierung + Session-Cookie |
| POST | `/auth/login` | Login + Session-Cookie |
| POST | `/auth/logout` | Session löschen |
| GET | `/auth/me` | Aktuelle Session |
| GET | `/workspaces` | Alle Workspaces des Users |
| POST | `/workspaces` | Workspace erstellen |
| GET | `/workspaces/:wid/blocks?parentId=` | Blöcke eines Parents |
| POST | `/workspaces/:wid/blocks` | Block erstellen |
| PATCH | `/workspaces/:wid/blocks/:id` | Block aktualisieren |
| DELETE | `/workspaces/:wid/blocks/:id` | Block löschen |
| POST | `/workspaces/:wid/blocks/reorder` | Block umsortieren |

---

## Lokales Setup

```bash
# PostgreSQL starten (via Homebrew, einmalig installiert)
brew services start postgresql@16

# Backend (Terminal 1)
cd /Users/babitzki/dev/notion-clone/backend
npm run dev   # → http://localhost:3001

# Frontend (Terminal 2)
cd /Users/babitzki/dev/notion-clone/frontend
npm run dev   # → http://localhost:5173
```

---

## Nächste Schritte (Post-MVP)

| Feature | Priorität |
|---------|-----------|
| Real-time Kollaboration (Yjs) | Hoch |
| Datenbank-Blöcke (Table/Board/Kanban) | Hoch |
| Seiten löschen + umbenennen via Sidebar-Menü | Mittel |
| Block-Drag-&-Drop (umsortieren) | Mittel |
| Suche (Meilisearch) | Mittel |
| Export (Markdown, PDF) | Niedrig |
| Mobile App (React Native) | Niedrig |
| Relations & Rollups | Niedrig |

---

## Entscheidungen & Trade-offs

| Entscheidung | Begründung |
|---|---|
| Tiptap-JSON-Blob pro Page | Einfacher als row-per-block für MVP; migrierbar zu v2 |
| Fractional Indexing (Float) | Insert-between ohne Renumbering aller Geschwister |
| Lucia v3 Session-Cookies | Einfacher als JWT, sofort revozierbar, kein Refresh-Token |
| Zustand für State | Konsistent mit floracity-Projekt |
| Vite Dev-Proxy `/api → :3001` | Einheitliche relative URLs in dev + prod (Nginx) |
| PostgreSQL via Homebrew | Docker nicht installiert; Homebrew-Setup unkomplizierter |
