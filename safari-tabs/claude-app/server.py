#!/usr/bin/env python3
"""MCP-Server für die Claude-App (macOS): Safari-Tabs aufräumen.

Stellt Claude drei Werkzeuge und einen Befehl („tabs-aufraeumen“) zur Verfügung:

  safari_tabs_ueberblick        Tabs lesen, Empfehlung + Ordnervorschläge
  safari_tabs_schliessen        ausgewählte Tabs schließen
  safari_lesezeichen_speichern  Tabs in vorhandene Lesezeichen-Ordner eintragen

Reines Python (Standardbibliothek), spricht MCP über stdio (JSON-RPC, eine
Nachricht pro Zeile). Nutzt die Logik aus safari_tabs.py.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):            # im Bundle: gleicher Ordner, im Repo: ../
    if (p / "safari_tabs.py").exists():
        sys.path.insert(0, str(p))
        break

import safari_tabs as st  # noqa: E402

SERVER_NAME = "safari-tabs"
SERVER_VERSION = "1.2.0"
OUT = sys.stdout                       # nur hier dürfen JSON-RPC-Nachrichten hin

# Zustand der letzten Analyse (Tab-Nummern beziehen sich darauf)
STATE: Dict[str, Any] = {"plan": None, "folders": [], "cfg": None}


# --------------------------------------------------------------------------
# Werkzeuge
# --------------------------------------------------------------------------
def tool_overview(args: Dict) -> Dict:
    cfg = st.load_config(None)
    tabs, devices, cloud_note = st.read_all_tabs(
        include_cloud=args.get("andere_geraete", True) is not False)
    root = st.load_bookmarks(quiet=True)
    folders = st.collect_folders(root) if root else []
    plan = st.analyze(tabs, cfg, st.bookmark_index(root, cfg["tracking_params"]))
    if folders:
        st.assign_folders(plan, folders, cfg)
    STATE.update(plan=plan, folders=folders, cfg=cfg)

    hosts: Dict[str, int] = {}
    for t in tabs:
        if t.host:
            h = st._bare_host(t.host)
            hosts[h] = hosts.get(h, 0) + 1

    def tab_info(t: st.Tab) -> Dict:
        d = {"nr": t.num, "geraet": t.device or "Mac", "titel": t.title, "url": t.url,
             "empfehlung": st.ACTION_LABEL[t.action]}
        if t.reason:
            d["grund"] = t.reason
        kind = t.kind.lstrip("~")
        if kind:
            d["art"] = st.KINDS[kind]["label"] + (" (vermutet)" if t.kind.startswith("~") else "")
        if t.action == st.BOOKMARK and t.target_path:
            d["ordner_vorschlag"] = t.target_path + (" (neu)" if t.target_new else "")
            if t.target_why:
                d["ordner_grund"] = t.target_why
        return d

    local, remote = st.split_local_remote(tabs)
    return {
        "zusammenfassung": {
            "tabs": len(tabs),
            "mac_tabs": len(local),
            "mac_fenster": len({t.window for t in local}),
            "andere_geraete": devices,
            "verschiedene_seiten": len(hosts),
            "haeufigste_seiten": sorted(hosts.items(), key=lambda x: -x[1])[:8],
            "schliessen": len(plan.by_action(st.CLOSE)),
            "lesezeichen": len(plan.by_action(st.BOOKMARK)),
            "offen_lassen": len(plan.by_action(st.KEEP)),
        },
        "lesezeichen_zugriff": bool(root),
        "icloud_tabs_hinweis": cloud_note,
        "hinweis": None if root else (
            "Kein Zugriff auf die Safari-Lesezeichen. Die Freigabe für die App „Claude“ "
            "reicht nicht: Das Python-Programm der Erweiterung braucht selbst den "
            "Festplattenvollzugriff. Rufe safari_zugriff_pruefen auf (mit "
            "einstellungen_oeffnen=true) und führe den Nutzer durch die Anleitung."),
        "zugriff": None if root else st.access_diagnosis(),
        "ordner": [{"nr": f.num, "pfad": f.path, "lesezeichen": f.leaves} for f in folders],
        "tabs": [tab_info(t) for t in plan.tabs],
    }


def _require_plan() -> st.Plan:
    if STATE["plan"] is None:
        raise ValueError("Bitte zuerst safari_tabs_ueberblick aufrufen.")
    return STATE["plan"]


def tool_close(args: Dict) -> Dict:
    plan = _require_plan()
    nums = {int(n) for n in args.get("nummern", [])}
    by_num = {t.num: t for t in plan.tabs}
    unknown = sorted(n for n in nums if n not in by_num)
    chosen = [by_num[n] for n in sorted(nums) if n in by_num]
    tabs, remote = st.split_local_remote(chosen)
    res = st.close_tabs(tabs) if tabs else {"closed": 0, "skipped": 0}
    for t in tabs:
        t.action, t.reason = st.CLOSE, "geschlossen"
    # Indizes in den Fenstern haben sich verschoben → für spätere Schritte neu
    # einlesen und Nummern über die URL zuordnen
    _refresh_positions(plan)
    out = {"geschlossen": res["closed"]}
    if res["skipped"]:
        out["uebersprungen"] = res["skipped"]
        out["hinweis"] = "Einige Tabs hatten sich inzwischen verändert und wurden nicht geschlossen."
    if remote:
        out["selbst_schliessen"] = [
            {"nr": t.num, "geraet": t.device, "titel": t.title, "url": t.url} for t in remote]
        out["hinweis_andere_geraete"] = (
            "Tabs auf iPhone/iPad können nicht automatisch geschlossen werden. Gib dem Nutzer "
            "eine Checkliste pro Gerät. Schließen: am iPhone in der Tab-Übersicht nach links "
            "wischen, oder am Mac in der Tab-Übersicht unter dem Gerät auf das x klicken.")
    if unknown:
        out["unbekannte_nummern"] = unknown
    return out


def _refresh_positions(plan: st.Plan) -> None:
    try:
        current = st.read_safari_tabs()
    except SystemExit:
        return
    pool: Dict[str, List[st.Tab]] = {}
    for c in current:
        pool.setdefault(c.url, []).append(c)
    for t in plan.tabs:
        if t.reason == "geschlossen" or t.remote:
            continue
        lst = pool.get(t.url)
        if lst:
            c = lst.pop(0)
            t.window, t.index = c.window, c.index


def _resolve_folder(name: str, folders: List[st.Folder]):
    n = name.strip().strip("/")
    low = n.lower()
    if low.endswith(" (neu)"):
        n, low = n[:-6], low[:-6]
    for f in folders:
        if low in (f.path.lower(), f.title.lower()):
            return f
    partial = [f for f in folders if low in f.title.lower() or low in f.path.lower()]
    return partial[0] if len(partial) == 1 else None


def tool_save(args: Dict) -> Dict:
    plan = _require_plan()
    folders: List[st.Folder] = STATE["folders"]
    cfg = STATE["cfg"]
    if not folders:
        raise ValueError("Kein Zugriff auf die Lesezeichen-Ordner (Festplattenvollzugriff für Claude fehlt).")
    by_num = {t.num: t for t in plan.tabs}
    to_save: List[st.Tab] = []
    new_folders = set()
    problems = []
    for e in args.get("eintraege", []):
        t = by_num.get(int(e.get("nummer", -1)))
        if not t:
            problems.append(f"Tab {e.get('nummer')} unbekannt")
            continue
        target = (e.get("ordner") or "").strip()
        if not target:
            problems.append(f"Tab {t.num}: kein Ordner angegeben")
            continue
        f = _resolve_folder(target, folders)
        if f:
            t.target_key, t.target_path, t.target_new = f.key, f.path, False
        else:
            if not args.get("neue_ordner_erlaubt", False):
                problems.append(f"Tab {t.num}: Ordner „{target}“ gibt es nicht "
                                "(neue Ordner nur mit neue_ordner_erlaubt=true)")
                continue
            clean = target[:-6].strip() if target.lower().endswith(" (neu)") else target
            st.set_new_target(t, clean)
            new_folders.add(t.target_path)
        to_save.append(t)
    if not to_save:
        return {"gespeichert": 0, "probleme": problems}

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = st.save_into_safari(to_save, cfg)
        closed = 0
        if ok and args.get("tabs_danach_schliessen"):
            keys = {st.normalize_url(t.url) for t in to_save}
            res = st.close_tabs([c for c in st.read_safari_tabs()
                                 if st.normalize_url(c.url) in keys])
            closed = res["closed"]
    # Safari wurde neu gestartet → Nummern gelten nicht mehr
    STATE["plan"] = None
    out = {"ok": ok, "protokoll": buf.getvalue().strip(), "neue_ordner": sorted(new_folders)}
    if closed:
        out["danach_geschlossen"] = closed
    if problems:
        out["probleme"] = problems
    if not ok:
        out["hinweis"] = ("Lesezeichen konnten nicht geschrieben werden: Das Python-Programm "
                          "der Erweiterung hat keinen Festplattenvollzugriff.")
        out["zugriff"] = st.access_diagnosis()
    return out


def tool_access(args: Dict) -> Dict:
    diag = st.access_diagnosis()
    if args.get("einstellungen_oeffnen"):
        st.open_access_settings()
        diag["geoeffnet"] = ("Die Einstellung „Festplattenvollzugriff“ ist geöffnet und "
                             "Python.app wird im Finder angezeigt – der Nutzer kann es "
                             "auch einfach in die Liste ziehen.")
    diag["alles_ok"] = diag["lesezeichen"] == "ok"
    return diag


TOOLS = {
    "safari_zugriff_pruefen": {
        "fn": tool_access,
        "description": (
            "Prüft, ob die Erweiterung auf Safari-Lesezeichen und iCloud-Tabs zugreifen darf, "
            "und nennt genau das Programm, das unter Festplattenvollzugriff freigegeben werden "
            "muss (Python.app, nicht nur Claude). Mit einstellungen_oeffnen=true werden die "
            "Systemeinstellung und Python.app im Finder geöffnet."),
        "inputSchema": {"type": "object", "properties": {
            "einstellungen_oeffnen": {"type": "boolean",
                                      "description": "Einstellungen + Finder öffnen"}}},
        "annotations": {"title": "Zugriff prüfen", "readOnlyHint": True},
    },
    "safari_tabs_ueberblick": {
        "fn": tool_overview,
        "description": (
            "Liest alle offenen Safari-Tabs des Macs und – über iCloud – von iPhone/iPad "
            "sowie die Lesezeichen-Ordner des Nutzers. Jeder Tab hat ein Feld 'geraet'. "
            "Liefert für jeden Tab eine Nummer, eine Empfehlung (schließen / Lesezeichen / "
            "behalten) mit Grund, die erkannte Inhaltsart und einen passenden vorhandenen "
            "Ordner. Ändert nichts."),
        "inputSchema": {"type": "object", "properties": {
            "andere_geraete": {"type": "boolean",
                               "description": "Tabs von iPhone/iPad (über iCloud) einbeziehen "
                                              "(Standard: true)"}}},
        "annotations": {"title": "Safari-Tabs: Überblick", "readOnlyHint": True},
    },
    "safari_tabs_schliessen": {
        "fn": tool_close,
        "description": (
            "Schließt die angegebenen Safari-Tabs (Nummern aus safari_tabs_ueberblick). "
            "Mac-Tabs werden direkt geschlossen; Tabs von iPhone/iPad kommen als Liste "
            "'selbst_schliessen' zurück, die der Nutzer selbst schließen muss. "
            "Nur aufrufen, nachdem der Nutzer die Liste ausdrücklich bestätigt hat."),
        "inputSchema": {
            "type": "object",
            "properties": {"nummern": {"type": "array", "items": {"type": "integer"},
                                       "description": "Tab-Nummern, die geschlossen werden"}},
            "required": ["nummern"],
        },
        "annotations": {"title": "Safari-Tabs schließen", "destructiveHint": True},
    },
    "safari_lesezeichen_speichern": {
        "fn": tool_save,
        "description": (
            "Trägt Tabs (auch von iPhone/iPad) als Lesezeichen in die angegebenen Ordner ein; "
            "über iCloud erscheinen sie auf allen Geräten (Pfad oder Name aus "
            "der Ordnerliste von safari_tabs_ueberblick). Safari wird dafür kurz beendet und "
            "wieder geöffnet; vorher wird eine Sicherung der Lesezeichen angelegt; vorhandene "
            "Lesezeichen werden nicht doppelt eingetragen. Nur nach ausdrücklicher "
            "Bestätigung des Nutzers aufrufen."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "eintraege": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nummer": {"type": "integer", "description": "Tab-Nummer"},
                            "ordner": {"type": "string", "description": "Ordnerpfad oder -name"},
                        },
                        "required": ["nummer", "ordner"],
                    },
                },
                "neue_ordner_erlaubt": {
                    "type": "boolean",
                    "description": "Nur true, wenn der Nutzer neuen Ordnern zugestimmt hat",
                },
                "tabs_danach_schliessen": {
                    "type": "boolean",
                    "description": "gespeicherte Tabs danach schließen (nur wenn gewünscht)",
                },
            },
            "required": ["eintraege"],
        },
        "annotations": {"title": "In Safari-Lesezeichen speichern", "destructiveHint": False},
    },
}

PROMPT_TEXT = """Hilf mir, meine Safari-Tabs aufzuräumen. Gehe so vor und antworte auf Deutsch:

1. Rufe `safari_tabs_ueberblick` auf.

2. **Überblick:** Fasse kurz zusammen: Tabs pro Gerät (Mac, iPhone, iPad …), häufigste Seiten, wie viel überflüssig ist. Falls `icloud_tabs_hinweis` gesetzt ist, erkläre kurz, warum iPhone-Tabs fehlen.

3. **Empfehlung – schließen:** Zeige eine Tabelle mit Nr., Gerät, Titel (kurz) und Grund für alle Tabs, die geschlossen werden sollten. Prüfe die Empfehlungen des Tools mit deinem eigenen Urteil: Ergänze offensichtlich erledigte Tabs (z. B. Bestell-/Versandbestätigungen, Paketverfolgung, Download-Seiten, einmalige Formulare) und nimm Tabs heraus, die eindeutig wichtig sind. Markiere deine eigenen Änderungen mit „(Claude)“.
   Frage mich dann, ob diese Tabs geschlossen werden sollen. Ich kann Nummern hinzufügen oder herausnehmen.
   Erst nach meinem OK: `safari_tabs_schliessen`. Mac-Tabs werden dabei automatisch geschlossen. Für Tabs auf iPhone/iPad gib mir danach eine kurze Checkliste pro Gerät (die muss ich selbst schließen) – erwähne auch die Einstellung „Tabs automatisch schließen“ am iPhone (Einstellungen → Apps → Safari → Tabs schließen).

4. **Einsortieren:** Zeige eine Tabelle mit Nr., Titel und Ziel-Ordner für die übrigen Tabs, die gespeichert werden sollen, gruppiert nach Ordner. Verwende meine vorhandenen Ordner aus der Ordnerliste. Für Tabs mit Vorschlag „Unsortiert (neu)“ oder unpassendem Vorschlag wähle selbst den passendsten vorhandenen Ordner anhand von Titel und URL. Schlage einen neuen Ordner nur vor, wenn wirklich nichts passt, und kennzeichne ihn als neu. Web-Apps mit Empfehlung „behalten“ bleiben offen.
   Frage mich, ob ich so speichern soll und ob die gespeicherten Tabs danach geschlossen werden sollen. Hinweis: Safari wird dafür kurz beendet und wieder geöffnet. Über iCloud erscheinen die Lesezeichen auch auf iPhone/iPad. „Danach schließen“ wirkt nur auf Mac-Tabs.
   Erst nach meinem OK: `safari_lesezeichen_speichern` (neue Ordner nur mit `neue_ordner_erlaubt: true`, wenn ich zugestimmt habe).

5. Bestätige zum Schluss kurz, was passiert ist (geschlossen, gespeichert pro Ordner).

Schließe oder speichere nie etwas ohne meine ausdrückliche Bestätigung. Falls `lesezeichen_zugriff` false ist: Rufe `safari_zugriff_pruefen` mit `einstellungen_oeffnen: true` auf und erkläre mir Schritt für Schritt, wie ich **Python.app** (Pfad aus `python_programm`) unter Festplattenvollzugriff hinzufüge. Die Freigabe nur für „Claude“ reicht nicht, weil die Erweiterung als eigenes Python-Programm läuft. Danach muss ich Claude mit ⌘Q beenden und neu öffnen. Wenn ich „weiter“ schreibe, prüfe den Zugriff erneut, bevor du weitermachst."""

PROMPTS = {
    "tabs-aufraeumen": {
        "description": "Safari-Tabs analysieren, Unnötige schließen, Rest in Lesezeichen-Ordner einsortieren",
        "text": PROMPT_TEXT,
    },
}


# --------------------------------------------------------------------------
# MCP / JSON-RPC
# --------------------------------------------------------------------------
def send(msg: Dict) -> None:
    OUT.write(json.dumps(msg, ensure_ascii=False) + "\n")
    OUT.flush()


def call_tool(name: str, args: Dict) -> Dict:
    spec = TOOLS.get(name)
    if not spec:
        return {"content": [{"type": "text", "text": f"Unbekanntes Werkzeug: {name}"}],
                "isError": True}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = spec["fn"](args or {})
        return {"content": [{"type": "text",
                             "text": json.dumps(result, ensure_ascii=False, indent=1)}]}
    except SystemExit as e:                # Fehlermeldungen aus safari_tabs (sys.exit)
        text = str(e.code) if e.code not in (None, 0) else "Abgebrochen."
        if "Terminal" in text:
            text = text.replace("Terminal", "Claude")
        return {"content": [{"type": "text", "text": text}], "isError": True}
    except Exception as e:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        return {"content": [{"type": "text", "text": f"Fehler: {e}"}], "isError": True}


def handle(req: Dict) -> Optional[Dict]:
    method = req.get("method", "")
    params = req.get("params") or {}
    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}, "prompts": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": ("Werkzeuge zum Aufräumen von Safari-Tabs. Erst Überblick zeigen, "
                             "Schließen und Speichern nur nach Bestätigung des Nutzers."),
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [
            {"name": n, "description": s["description"], "inputSchema": s["inputSchema"],
             "annotations": s["annotations"]} for n, s in TOOLS.items()]}
    if method == "tools/call":
        return call_tool(params.get("name", ""), params.get("arguments") or {})
    if method == "prompts/list":
        return {"prompts": [{"name": n, "description": p["description"], "arguments": []}
                            for n, p in PROMPTS.items()]}
    if method == "prompts/get":
        p = PROMPTS.get(params.get("name", ""))
        if not p:
            raise KeyError("Unbekannter Befehl")
        return {"description": p["description"],
                "messages": [{"role": "user", "content": {"type": "text", "text": p["text"]}}]}
    if method in ("resources/list",):
        return {"resources": []}
    raise NotImplementedError(method)


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None,
                  "error": {"code": -32700, "message": "Parse error"}})
            continue
        if "id" not in req:            # Benachrichtigung (z. B. notifications/initialized)
            continue
        try:
            result = handle(req)
            send({"jsonrpc": "2.0", "id": req["id"], "result": result})
        except NotImplementedError as e:
            send({"jsonrpc": "2.0", "id": req["id"],
                  "error": {"code": -32601, "message": f"Method not found: {e}"}})
        except Exception as e:  # noqa: BLE001
            send({"jsonrpc": "2.0", "id": req["id"],
                  "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
