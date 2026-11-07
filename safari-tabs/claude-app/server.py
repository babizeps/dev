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
import copy
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
SERVER_VERSION = "1.9.0"
OUT = sys.stdout                       # nur hier dürfen JSON-RPC-Nachrichten hin

# Zustand der letzten Analyse (Tab-Nummern beziehen sich darauf)
STATE: Dict[str, Any] = {"plan": None, "folders": [], "cfg": None}


# --------------------------------------------------------------------------
# Werkzeuge
# --------------------------------------------------------------------------
def tool_overview(args: Dict) -> Dict:
    cfg = st.load_config(None)
    bridge_error = None
    try:
        root, mode, cloud_copy = st.load_bookmarks_any(allow_terminal=True)
    except st.BridgeError as e:
        root, mode, cloud_copy, bridge_error = None, "", None, str(e)
    try:
        tabs, devices, cloud_note = st.read_all_tabs(
            include_cloud=args.get("andere_geraete", True) is not False,
            cloud_db=cloud_copy)
    finally:
        if mode == "terminal":
            st.cleanup_bridge_copies()
    folders = st.collect_folders(root) if root else []
    plan = st.analyze(tabs, cfg, st.bookmark_index(root, cfg["tracking_params"]))
    if folders:
        st.assign_folders(plan, folders, cfg)
    STATE.update(plan=plan, folders=folders, cfg=cfg, mode=mode, root=root)

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
        "zugriff_ueber": {"direkt": "direkt", "terminal": "Terminal (Umweg)"}.get(mode, "keiner"),
        "icloud_tabs_hinweis": cloud_note,
        "hinweis": (
            "Die Lesezeichen wurden über ein kurz geöffnetes Terminal-Fenster gelesen, weil "
            "die Erweiterung selbst keinen Festplattenvollzugriff hat. Das Fenster kann "
            "geschlossen werden." if mode == "terminal" else None) if root else (
            "Kein Zugriff auf die Safari-Lesezeichen – auch nicht über Terminal. "
            + (bridge_error or "") + " Danach erneut versuchen."),
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
        try:
            f, new_path = st.resolve_target(target, folders)
        except st.AmbiguousFolder as e:
            problems.append(f"Tab {t.num}: {e}")
            continue
        if f:
            t.target_key, t.target_path, t.target_new = f.key, f.path, False
        else:
            if not args.get("neue_ordner_erlaubt", False):
                problems.append(f"Tab {t.num}: Ordner „{new_path}“ gibt es nicht "
                                "(neue Ordner/Unterordner nur mit neue_ordner_erlaubt=true)")
                continue
            st.set_new_target(t, new_path)
            new_folders.add(t.target_path)
        to_save.append(t)
    if not to_save:
        return {"gespeichert": 0, "probleme": problems}
    rule_problems = st.check_new_folders(to_save)
    if rule_problems:
        return {"ok": False, "nichts_geaendert": True, "regelverstoesse": rule_problems,
                "probleme": problems, "regeln": RULES_TEXT}

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = st.save_into_safari(to_save, cfg, via_terminal=STATE.get("mode") == "terminal")
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
        out["hinweis"] = ("Lesezeichen konnten nicht geschrieben werden (Details im Protokoll). "
                          "Meist fehlt Terminal der Festplattenvollzugriff.")
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


# --------------------------------------------------------------------------
# Korrigieren: suchen, entfernen, rückgängig, Sicherung zurückspielen
# --------------------------------------------------------------------------
ICLOUD_NOTE = ("Ist Safari in iCloud eingeschaltet, kann iCloud gelöschte Einträge in seltenen "
               "Fällen wieder zurückbringen. Prüfe nach etwa einer Minute mit "
               "safari_lesezeichen_suchen; tauchen sie wieder auf, muss der Nutzer sie in "
               "Safari mit ⌥⌘B (Lesezeichen bearbeiten) → Rechtsklick → Löschen entfernen.")


def _read_root() -> Dict:
    try:
        root, mode, _ = st.load_bookmarks_any(allow_terminal=True)
    except st.BridgeError as e:
        raise ValueError(str(e))
    finally:
        st.cleanup_bridge_copies()
    if not root:
        raise ValueError("Kein Zugriff auf die Lesezeichen. " + st.TERMINAL_FDA_HINT)
    return root


def tool_search(args: Dict) -> Dict:
    root = _read_root()
    hits = st.search_bookmarks(root, args.get("suche", ""), args.get("ordner"),
                               limit=int(args.get("max", 50)))
    return {"treffer": hits, "anzahl": len(hits)}


def tool_history(_: Dict) -> Dict:
    hist = st.load_history()[-10:]
    try:
        backups = st.list_backups()
    except PermissionError:
        try:
            backups = st.run_via_terminal("list").get("sicherungen", [])
        except st.BridgeError as e:
            backups = [{"fehler": str(e)}]
    return {
        "aenderungen": [
            {"zeit": e.get("zeit"), "aktion": e.get("aktion"), "sicherung": e.get("sicherung"),
             "hinzugefuegt": e.get("hinzugefuegt", []), "entfernt": e.get("entfernt", []),
             "ordner_neu": e.get("ordner_neu", []),
             "rueckgaengig_gemacht": e.get("rueckgaengig_gemacht", False)}
            for e in reversed(hist)],
        "sicherungen": backups[:15],
        "hinweis": None if hist else (
            "Noch kein Verlauf – Speicherungen mit älteren Versionen wurden nicht "
            "protokolliert. Einzelne Einträge lassen sich trotzdem per URL oder Titel+Ordner "
            "entfernen (safari_lesezeichen_suchen hilft beim Finden)."),
    }


def _finish(res: Dict, extra: Optional[Dict] = None) -> Dict:
    STATE["plan"] = None          # Safari wurde neu gestartet → Tab-Nummern ungültig
    if not res.get("ok"):
        return {"ok": False, "fehler": res.get("fehler"), "zugriff": st.access_diagnosis()}
    out = {k: v for k, v in res.items() if k in (
        "ok", "aktion", "sicherung", "entfernt", "wiederhergestellt", "ergebnis")}
    if res.get("umstrukturiert"):
        out["umstrukturiert"] = [_summarize(r) for r in res["umstrukturiert"]]
    out.update(extra or {})
    return out


RULES_TEXT = (
    "Ordner-Regeln: (1) von breit zu spezifisch – oben breite Themen, darunter feinere; ein "
    "Ordner darf nicht nur aus genau einem Unterordner bestehen; höchstens 3 Ebenen. "
    "(2) Jeder neue oder neu befüllte Ordner enthält mindestens 2 Einträge (inkl. "
    "Unterordnern). (3) Keine Sammelnamen wie „Sonstiges“, „Misc“, „Allgemein“, „Diverses“, "
    "„Andere“, „Neu“ – Einträge, die nirgends passen, bleiben direkt im übergeordneten Ordner "
    "oder als Tab offen.")


def _summarize(r: Dict) -> Dict:
    """Ergebnis einer Umstrukturierung ohne den (großen) Schnappschuss."""
    counts: Dict[str, int] = {}
    for m in r.get("verschoben", []):
        counts[m["nach"]] = counts.get(m["nach"], 0) + 1
    for a in r.get("hinzugefuegt", []):
        counts[a["ordner"]] = counts.get(a["ordner"], 0) + 1
    out = {"ordner": r.get("ordner"),
           "neue_unterordner": [o["titel"] for o in r.get("ordner_neu", [])],
           "verschoben": len(r.get("verschoben", [])),
           "hinzugefuegt": len(r.get("hinzugefuegt", [])),
           "pro_unterordner": dict(sorted(counts.items())),
           "leere_entfernt": r.get("leer_entfernt", [])}
    if r.get("nicht_gefunden"):
        out["nicht_gefunden"] = r["nicht_gefunden"]
    return {k: v for k, v in out.items() if v not in ([], {}, None) or k == "ordner"}


def _apply(change: Dict, extra_note: Optional[str] = None) -> Dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = st.apply_bookmark_change(change)
    out = _finish(res, {"protokoll": buf.getvalue().strip()})
    if res.get("ok") and extra_note:
        out["hinweis"] = extra_note
    return out


def tool_undo(args: Dict) -> Dict:
    entry = st.last_undoable()
    if not entry:
        raise ValueError("Im Verlauf gibt es nichts, was sich rückgängig machen lässt. Einzelne "
                         "Lesezeichen lassen sich mit safari_lesezeichen_entfernen löschen.")
    change = st.undo_change_for(entry, force=bool(args.get("erzwingen")))
    out = _apply(change, ICLOUD_NOTE)
    if out.get("ok"):
        st.mark_undone(entry)
        out["rueckgaengig_gemacht"] = {"aktion": entry.get("aktion"), "zeit": entry.get("zeit")}
    return out


def tool_remove(args: Dict) -> Dict:
    items = [e for e in args.get("eintraege", []) if isinstance(e, dict)]
    for e in items:
        if not (e.get("id") or e.get("url") or (e.get("titel") and e.get("ordner"))):
            raise ValueError("Jeder Eintrag braucht id, url oder titel+ordner.")
    entry = None
    change: Dict = {"remove": items, "aktion": "Lesezeichen entfernt"}
    if args.get("letzte_speicherung_rueckgaengig"):
        if not items:
            return tool_undo({})
        entry = st.last_undoable()
        if not entry or entry.get("umstrukturiert"):
            raise ValueError("Die letzte Änderung war keine einfache Speicherung – bitte "
                             "safari_rueckgaengig verwenden.")
        undo = st.undo_change_for(entry)
        change = {"remove": undo["remove"] + items,
                  "remove_folder_ids": undo["remove_folder_ids"], "aktion": undo["aktion"]}
    if not change["remove"]:
        raise ValueError("Nichts zum Entfernen angegeben.")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = st.apply_bookmark_change(change)
    if res.get("ok") and entry:
        st.mark_undone(entry)
    out = _finish(res, {"protokoll": buf.getvalue().strip()})
    if res.get("ok"):
        found = len(res.get("entfernt", []))
        if found < len(change["remove"]):
            out["nicht_gefunden"] = len(change["remove"]) - found
        out["hinweis"] = ICLOUD_NOTE
    return out


def tool_restore(args: Dict) -> Dict:
    name = (args.get("sicherung") or "").strip()
    if not name:
        raise ValueError("Name der Sicherung fehlt (siehe safari_lesezeichen_verlauf).")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = st.apply_bookmark_change({"restore": name})
    out = _finish(res, {"protokoll": buf.getvalue().strip()})
    if res.get("ok"):
        out["hinweis"] = ("Der Stand vor dem Zurückspielen ist als „" + res["sicherung"] +
                          "“ gesichert. " + ICLOUD_NOTE.replace("gelöschte Einträge",
                                                                "den alten Stand"))
    return out


def _root_for_structure() -> Dict:
    root = STATE.get("root")
    return root if root else _read_root()


def tool_subfolders(args: Dict) -> Dict:
    """Daten für eine verschachtelte Ordnerstruktur (ein Ordner oder alle Ziel-Ordner)."""
    root = _root_for_structure()
    plan = STATE.get("plan")
    folders = STATE.get("folders") or st.collect_folders(root)
    include = args.get("vorhandene_einbeziehen", True) is not False
    if args.get("ordner"):
        f = st.find_folder(args["ordner"], folders)
        if not f:
            raise ValueError(f"Ordner „{args['ordner']}“ nicht gefunden.")
        paths = [f.path]
    else:
        if not plan:
            raise ValueError("Ordner angeben oder vorher safari_tabs_ueberblick aufrufen.")
        counts: Dict[str, int] = {}
        for t in plan.by_action(st.BOOKMARK):
            top = next((f.path for f in folders if f.depth <= 1 and (
                t.target_path == f.path or t.target_path.startswith(f.path + "/"))
                and f.title not in st.SPECIAL_TITLES.values()), None)
            if top:
                counts[top] = counts.get(top, 0) + 1
        paths = [p for p, n in sorted(counts.items(), key=lambda x: -x[1])
                 if n >= int(args.get("mindestens_tabs", 3))]
    return {
        "ordner": [st.structure_hints(plan, root, p, include) for p in paths],
        "anleitung": (
            "Entwirf je Ordner eine verschachtelte Struktur von breit zu spezifisch "
            "(höchstens 3 Ebenen, z. B. Musik → Lofi): oben breite Themen, darunter feinere "
            "Unterteilungen nur, wenn ein Thema genug Einträge für mindestens zwei "
            "Untergruppen mit je ≥ 2 Einträgen hat. Kurze, konkrete Namen in der Sprache der "
            "vorhandenen Ordner; vorhandene Unterordner wiederverwenden. Einzelstücke bleiben "
            "direkt im Ordner (pfad \"\") – niemals in Sammelordner. Neue Tabs (nr) und "
            "vorhandene Lesezeichen (id) gemeinsam einordnen. Zeige den Baum (Ordner "
            "alphabetisch) mit Anzahl und Beispieltiteln, warte auf OK, dann "
            "safari_ordnerstruktur_anwenden. " + RULES_TEXT),
    }


def tool_apply_structure(args: Dict) -> Dict:
    root = _root_for_structure()
    folders = STATE.get("folders") or st.collect_folders(root)
    f = st.find_folder(args.get("ordner", ""), folders)
    if not f:
        raise ValueError(f"Ordner „{args.get('ordner')}“ nicht gefunden.")
    plan = STATE.get("plan")
    by_num = {t.num: t for t in plan.tabs} if plan else {}
    tree, problems = [], []
    for node in args.get("baum", []):
        rel = (node.get("pfad") or "").strip().strip("/")
        if len([p for p in rel.split("/") if p]) > 4:
            problems.append(f"„{rel}“ ist tiefer als 4 Ebenen – übersprungen")
            continue
        new_tabs = []
        for n in node.get("tab_nummern", []):
            t = by_num.get(int(n))
            if not t:
                problems.append(f"Tab {n} unbekannt (vorher safari_tabs_ueberblick aufrufen)")
                continue
            new_tabs.append(st._tab_to_dict(t))
        tree.append({"pfad": rel, "ids": list(node.get("lesezeichen_ids", [])),
                     "neu": new_tabs})
    if not tree:
        raise ValueError("Leere Struktur. " + " ".join(problems))
    spec = {"ordner": f.path, "baum": tree,
            "sortieren": args.get("sortieren", True) is not False,
            "leere_entfernen": args.get("leere_entfernen", True) is not False}
    # Probelauf auf einer Kopie: Regeln prüfen, bevor Safari beendet wird
    try:
        trial = st.restructure_folder(copy.deepcopy(root), spec, STATE.get("cfg")
                                      or st.load_config(None))
    except st.StructureError as e:
        return {"ok": False, "nichts_geaendert": True, "regelverstoesse": e.problems,
                "regeln": RULES_TEXT}
    if trial.get("nicht_gefunden"):
        problems.append(f"{len(trial['nicht_gefunden'])} Lesezeichen-ids nicht im Ordner gefunden")
    out = _apply({"restructure": [spec], "aktion": f"Ordnerstruktur in „{f.path}“"},
                 "Mit safari_rueckgaengig lässt sich die ganze Umstrukturierung zurücknehmen. "
                 + ICLOUD_NOTE.replace("gelöschte Einträge", "verschobene Einträge"))
    if problems:
        out["probleme"] = problems
    STATE["root"] = None
    return out


def tool_sort(args: Dict) -> Dict:
    root = _root_for_structure()
    f = st.find_folder(args.get("ordner", ""), STATE.get("folders") or st.collect_folders(root))
    if not f:
        raise ValueError(f"Ordner „{args.get('ordner')}“ nicht gefunden.")
    out = _apply({"sort": [f.path]})
    STATE["root"] = None
    return out


def tool_auto_setup(args: Dict) -> Dict:
    opts = {k: args.get(k) for k in ("haeufigkeit", "inaktiv_minuten",
                                     "gespeicherte_schliessen", "min_score", "ordnen")}
    res = st.install_automation(opts)
    res["hinweis"] = (
        "Die Automatik prüft stündlich im Hintergrund und räumt auf, wenn sie fällig ist und "
        "der Mac gerade nicht benutzt wird. Sie schließt eindeutig überflüssige Tabs, "
        "speichert Tabs mit sicherer Zuordnung und ordnet (wenn ordnen=true) alle Ordner: "
        "lose Lesezeichen kommen in thematische Unterordner nach den Regeln (breit → "
        "spezifisch, ≥ 2 Einträge, keine Sammelnamen), alles wird sortiert. Eigene "
        "Unterordner und die Reihenfolge der Hauptordner bleiben. Unsichere Tabs bleiben "
        "offen und stehen im Bericht. Jeder Lauf ist rückgängig machbar. macOS fragt gleich, "
        "ob Python Safari steuern darf → erlauben.")
    return res


def tool_auto_status(_: Dict) -> Dict:
    return st.automation_status()


def tool_auto_preview(_: Dict) -> Dict:
    root = _read_root()
    cfg = st.load_config(None)
    return {"wuerde_ordnen": st.describe_organize(root, cfg),
            "hinweis": ("Vorschau für die vorhandenen Lesezeichen (ändert nichts). Beim Lauf "
                        "kommen eindeutig zuordenbare Tabs dazu und werden mit eingeordnet.")}


def tool_auto_off(_: Dict) -> Dict:
    return st.uninstall_automation()


TOOLS = {
    "safari_automatik_einrichten": {
        "fn": tool_auto_setup,
        "description": (
            "Richtet die regelmäßige, selbständige Aufräum-Automatik ein (macOS-Hintergrunddienst). "
            "Sie läuft monatlich (oder wöchentlich/täglich), aber nur wenn der Mac eine Weile nicht "
            "benutzt wird: schließt eindeutig überflüssige Tabs, speichert Tabs mit sicherer "
            "Zuordnung und ordnet alles – lose Lesezeichen in thematische, verschachtelte "
            "Unterordner (breit → spezifisch, ≥ 2 Einträge, keine Sammelnamen) und sortiert. "
            "Bericht + Mitteilung nach jedem Lauf, jeder Lauf rückgängig machbar. Nur nach "
            "Zustimmung des Nutzers einrichten."),
        "inputSchema": {"type": "object", "properties": {
            "haeufigkeit": {"type": "string", "enum": ["monatlich", "woechentlich", "taeglich"],
                            "description": "Standard: monatlich"},
            "ordnen": {"type": "boolean",
                       "description": "bei jedem Lauf alles ordnen: Unterordner bilden und sortieren (Standard true)"},
            "inaktiv_minuten": {"type": "integer",
                                "description": "nur laufen, wenn der Mac so lange unbenutzt ist (Standard 15)"},
            "gespeicherte_schliessen": {"type": "boolean",
                                        "description": "gespeicherte Tabs danach schließen (Standard false)"},
            "min_score": {"type": "number",
                          "description": "Mindest-Sicherheit der Ordner-Zuordnung (Standard 10)"}}},
        "annotations": {"title": "Automatik einrichten", "destructiveHint": False},
    },
    "safari_automatik_vorschau": {
        "fn": tool_auto_preview,
        "description": ("Zeigt, welche Unterordner die Automatik beim nächsten Lauf anlegen und "
                        "wie viele Lesezeichen sie verschieben würde. Ändert nichts."),
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"title": "Automatik-Vorschau", "readOnlyHint": True},
    },
    "safari_automatik_status": {
        "fn": tool_auto_status,
        "description": "Zeigt, ob die Automatik läuft, ihre Einstellungen und das letzte Ergebnis (mit Bericht).",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"title": "Automatik-Status", "readOnlyHint": True},
    },
    "safari_automatik_beenden": {
        "fn": tool_auto_off,
        "description": "Schaltet die Automatik aus (entfernt den Hintergrunddienst).",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"title": "Automatik ausschalten", "destructiveHint": False},
    },
    "safari_unterordner_vorschlagen": {
        "fn": tool_subfolders,
        "description": (
            "Liefert für einen Ordner (oder alle Ziel-Ordner der aktuellen Tabs) alle Einträge "
            "– neue Tabs (nr) und vorhandene Lesezeichen (id, jetziger Unterordner) – samt "
            "vorhandener Unterordner, häufiger Websites und Stichwörter. Grundlage, um eine "
            "verschachtelte, smarte Unterordner-Struktur zu entwerfen. Ändert nichts."),
        "inputSchema": {"type": "object", "properties": {
            "ordner": {"type": "string", "description": "z. B. „Video“ – leer = alle Ziel-Ordner der Tabs"},
            "vorhandene_einbeziehen": {"type": "boolean",
                                       "description": "vorhandene Lesezeichen mit einordnen (Standard true)"},
            "mindestens_tabs": {"type": "integer",
                                "description": "ohne ordner: nur Ordner mit so vielen Tabs (Standard 3)"}}},
        "annotations": {"title": "Unterordner vorschlagen", "readOnlyHint": True},
    },
    "safari_ordnerstruktur_anwenden": {
        "fn": tool_apply_structure,
        "description": (
            "Legt in einem vorhandenen Ordner eine verschachtelte Unterordner-Struktur an, "
            "verschiebt vorhandene Lesezeichen (ids aus safari_unterordner_vorschlagen) und "
            "trägt Tabs (nummern aus safari_tabs_ueberblick) ein, entfernt dadurch leer "
            "gewordene Unterordner und sortiert (Unterordner alphabetisch zuerst, dann "
            "Lesezeichen nach Website und Titel). Prüft vorher die "
            "Ordner-Regeln (≥ 2 Einträge je Ordner, keine Sammelnamen wie „Sonstiges“, kein "
            "Ordner nur mit einem Unterordner) – bei Verstößen wird nichts geändert und "
            "'regelverstoesse' zurückgegeben. Safari wird kurz "
            "beendet, vorher gesichert, komplett rückgängig machbar. Nur nach ausdrücklicher "
            "Bestätigung des Nutzers aufrufen."),
        "inputSchema": {"type": "object", "properties": {
            "ordner": {"type": "string", "description": "vorhandener Ordner, z. B. „Video“"},
            "baum": {"type": "array", "description": "eine Zeile pro Ziel-Unterordner", "items": {
                "type": "object", "properties": {
                    "pfad": {"type": "string",
                             "description": "relativ zum Ordner, z. B. „Musik/Lofi“; \"\" = direkt im Ordner"},
                    "lesezeichen_ids": {"type": "array", "items": {"type": "string"}},
                    "tab_nummern": {"type": "array", "items": {"type": "integer"}}},
                "required": ["pfad"]}},
            "sortieren": {"type": "boolean", "description": "smart sortieren (Standard true)"},
            "leere_entfernen": {"type": "boolean",
                                "description": "durch Verschieben leer gewordene Unterordner entfernen (Standard true)"}},
            "required": ["ordner", "baum"]},
        "annotations": {"title": "Ordnerstruktur anwenden", "destructiveHint": True},
    },
    "safari_ordner_sortieren": {
        "fn": tool_sort,
        "description": (
            "Sortiert einen Lesezeichen-Ordner samt Unterordnern: Unterordner zuerst "
            "(alphabetisch, vorhandene Sammelordner wie „Sonstiges“ zuletzt), dann "
            "Lesezeichen nach Website und Titel. "
            "Rückgängig machbar. Nur nach Bestätigung."),
        "inputSchema": {"type": "object", "properties": {"ordner": {"type": "string"}},
                        "required": ["ordner"]},
        "annotations": {"title": "Ordner sortieren", "destructiveHint": False},
    },
    "safari_rueckgaengig": {
        "fn": tool_undo,
        "description": (
            "Macht die letzte Änderung dieses Tools rückgängig – Speicherung, Ordnerstruktur "
            "oder Sortierung. Wurde ein umstrukturierter Ordner danach verändert, wird "
            "abgebrochen (mit erzwingen=true trotzdem). Nur nach Bestätigung."),
        "inputSchema": {"type": "object", "properties": {"erzwingen": {"type": "boolean"}}},
        "annotations": {"title": "Rückgängig", "destructiveHint": True},
    },
    "safari_lesezeichen_suchen": {
        "fn": tool_search,
        "description": (
            "Sucht Lesezeichen nach Text in Titel/URL (optional nur in einem Ordner) und "
            "liefert id, Titel, URL und Ordner. Zum Finden falscher Einträge vor dem Entfernen "
            "und zum Prüfen danach. Ändert nichts."),
        "inputSchema": {"type": "object", "properties": {
            "suche": {"type": "string", "description": "Text in Titel oder URL (leer = alle)"},
            "ordner": {"type": "string", "description": "nur in diesem Ordner (Name oder Pfad)"},
            "max": {"type": "integer", "description": "maximale Trefferzahl (Standard 50)"}}},
        "annotations": {"title": "Lesezeichen suchen", "readOnlyHint": True},
    },
    "safari_lesezeichen_verlauf": {
        "fn": tool_history,
        "description": (
            "Zeigt die letzten Änderungen dieses Tools an den Lesezeichen (was wann in welchen "
            "Ordner eingetragen oder entfernt wurde, mit ids) und die vorhandenen Sicherungen. "
            "Ändert nichts."),
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"title": "Lesezeichen-Verlauf", "readOnlyHint": True},
    },
    "safari_lesezeichen_entfernen": {
        "fn": tool_remove,
        "description": (
            "Entfernt Lesezeichen, z. B. nach einer falschen Zuordnung. Einträge per id (aus "
            "Verlauf/Suche), per url (optional mit ordner) oder per titel+ordner. Mit "
            "letzte_speicherung_rueckgaengig=true werden alle Lesezeichen der letzten "
            "Speicherung entfernt (und dabei neu angelegte, leere Ordner). Ordner selbst und "
            "andere Lesezeichen bleiben erhalten. Safari wird kurz beendet, vorher wird "
            "gesichert. Vorher dem Nutzer genau zeigen, was entfernt wird, und nur nach "
            "ausdrücklicher Bestätigung aufrufen. Bevorzugt gegenüber dem Zurückspielen einer "
            "Sicherung."),
        "inputSchema": {"type": "object", "properties": {
            "eintraege": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "string"}, "url": {"type": "string"},
                "titel": {"type": "string"}, "ordner": {"type": "string"}}}},
            "letzte_speicherung_rueckgaengig": {"type": "boolean"}}},
        "annotations": {"title": "Lesezeichen entfernen", "destructiveHint": True},
    },
    "safari_sicherung_zurueckspielen": {
        "fn": tool_restore,
        "description": (
            "Setzt alle Lesezeichen auf eine Sicherung zurück (Name aus "
            "safari_lesezeichen_verlauf). Alle späteren Änderungen – auch eigene des Nutzers – "
            "gehen verloren; der aktuelle Stand wird vorher gesichert. Nur verwenden, wenn "
            "gezieltes Entfernen nicht reicht, und nur nach ausdrücklicher Bestätigung."),
        "inputSchema": {"type": "object", "properties": {
            "sicherung": {"type": "string", "description": "z. B. Bookmarks.plist.backup-20261107-111423"}},
            "required": ["sicherung"]},
        "annotations": {"title": "Sicherung zurückspielen", "destructiveHint": True},
    },
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
                            "ordner": {"type": "string", "description": (
                                "Ordnerpfad oder -name; Unterordner mit „/“, z. B. "
                                "„Video/Musik“ (wird bei neue_ordner_erlaubt=true im "
                                "vorhandenen Ordner „Video“ angelegt)")},
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

4. **Einsortieren:** Zeige eine Tabelle mit Nr., Titel und Ziel-Ordner für die übrigen Tabs, die gespeichert werden sollen, gruppiert nach Ordner. Verwende meine vorhandenen Ordner aus der Ordnerliste. Für Tabs ohne `ordner_vorschlag` oder mit unpassendem Vorschlag wähle selbst den passendsten vorhandenen Ordner anhand von Titel und URL. Einen neuen (Unter-)Ordner schlägst du nur vor, wenn mindestens 2 Tabs hineinpassen, mit konkretem Namen – nie „Sonstiges“, „Unsortiert“, „Misc“ o. Ä. Passt ein einzelner Tab nirgends, schlag vor, ihn offen zu lassen oder in den thematisch nächsten vorhandenen Ordner zu legen. Web-Apps mit Empfehlung „behalten“ bleiben offen.
   Frage mich, ob ich so speichern soll und ob die gespeicherten Tabs danach geschlossen werden sollen. Hinweis: Safari wird dafür kurz beendet und wieder geöffnet. Über iCloud erscheinen die Lesezeichen auch auf iPhone/iPad. „Danach schließen“ wirkt nur auf Mac-Tabs.
   Erst nach meinem OK: `safari_lesezeichen_speichern` (neue Ordner nur mit `neue_ordner_erlaubt: true`, wenn ich zugestimmt habe).

5. Bestätige zum Schluss kurz, was passiert ist (geschlossen, gespeichert pro Ordner).

Schließe oder speichere nie etwas ohne meine ausdrückliche Bestätigung. Zugriff: Hat die Erweiterung selbst keinen Festplattenvollzugriff, liest und schreibt sie die Lesezeichen über ein kurz geöffnetes Terminal-Fenster (`zugriff_ueber`: Terminal). Sag mir dann kurz, dass ich das Fenster schließen kann. Ist `lesezeichen_zugriff` trotzdem false, erkläre mir genau den `hinweis` (meist: Festplattenvollzugriff für **Terminal** einschalten) und rufe danach auf mein „weiter“ hin `safari_tabs_ueberblick` erneut auf.

Unterordner: Passen in einen Ordner viele Tabs zu verschiedenen Themen, biete an, mit `safari_unterordner_vorschlagen` eine verschachtelte Struktur (höchstens 3 Ebenen) für Tabs und vorhandene Lesezeichen zu entwerfen; zeig sie als Baum und wende sie nach meinem OK mit `safari_ordnerstruktur_anwenden` an.

Automatik: Auf Wunsch richte ich mit `safari_automatik_einrichten` ein regelmäßiges, selbständiges Aufräumen und Ordnen ein (Standard monatlich, nur wenn der Mac unbenutzt ist). Erkläre vorher kurz, was sie automatisch tut (überflüssige Tabs schließen, sicher Zuordenbares speichern, alles in Unterordner ordnen und sortieren – Unsicheres bleibt offen), zeig die `safari_automatik_vorschau` und richte sie erst nach OK ein. Hat die Automatik Tabs „zur Prüfung“ übrig gelassen (`safari_automatik_status`), biete an, diese jetzt gemeinsam einzusortieren.

Korrekturen: Ist etwas falsch eingetragen, nutze `safari_lesezeichen_verlauf` bzw. `safari_lesezeichen_suchen`, zeig mir genau, was entfernt würde, und entferne es nach meinem OK mit `safari_lesezeichen_entfernen` (für die ganze letzte Änderung – auch Umstrukturierungen und Sortierungen: `safari_rueckgaengig`). Danach trägst du – wieder nach OK – die richtigen Einträge mit `safari_lesezeichen_speichern` ein (dafür vorher `safari_tabs_ueberblick` aufrufen). Eine Sicherung zurückspielen (`safari_sicherung_zurueckspielen`) nur, wenn gezieltes Entfernen nicht reicht. Prüfe nach dem Entfernen nach etwa einer Minute mit `safari_lesezeichen_suchen`, ob iCloud die Einträge zurückgebracht hat."""

PROMPTS = {
    "tabs-aufraeumen": {
        "description": "Safari-Tabs analysieren, Unnötige schließen, Rest in Lesezeichen-Ordner einsortieren",
        "text": PROMPT_TEXT,
    },
    "unterordner-erstellen": {
        "description": "Verschachtelte, smart geordnete Unterordner für Tabs und Lesezeichen",
        "text": (
            "Hilf mir, meine Lesezeichen-Ordner mit verschachtelten, smart geordneten "
            "Unterordnern zu strukturieren – für meine offenen Tabs und die Lesezeichen, die "
            "schon in den Ordnern liegen. Antworte auf Deutsch.\n"
            "1. Rufe `safari_tabs_ueberblick` und dann `safari_unterordner_vorschlagen` auf "
            "(ohne ordner = alle Ziel-Ordner; einzelne Ordner wie „Video“ gehen auch).\n"
            "2. Entwirf pro Ordner eine Struktur von breit zu spezifisch (höchstens 3 Ebenen): "
            "oben breite Themen, darunter feinere Unterteilungen nur, wenn es mindestens zwei "
            "Untergruppen mit je ≥ 2 Einträgen gibt. Jeder Ordner hat mindestens 2 Einträge. "
            "Konkrete, kurze Namen in der Sprache meiner Ordner – keine Sammelnamen wie "
            "„Sonstiges“, „Misc“, „Allgemein“. Einzelstücke bleiben direkt im Ordner. "
            "Vorhandene Unterordner wiederverwenden.\n"
            "3. Zeig mir den Baum eingerückt mit Anzahl und 2–3 Beispieltiteln, z. B.\n"
            "   Video\n   ├─ Musik (12)\n   │  ├─ Lofi (5)\n   │  └─ Jazz (4)\n"
            "   └─ Programmieren (7)\n"
            "   und sag dazu, wie viele vorhandene Lesezeichen verschoben würden.\n"
            "4. Ich kann umbenennen, zusammenlegen, Ebenen streichen oder Einträge verschieben.\n"
            "5. Erst nach meinem OK: `safari_ordnerstruktur_anwenden` pro Ordner (Safari wird "
            "kurz beendet). Meldet das Werkzeug `regelverstoesse`, wurde nichts geändert: "
            "passe den Baum an, zeig mir die Änderung und frag erneut.\n"
            "6. Erwähne, dass „mach das rückgängig“ (`safari_rueckgaengig`) alles zurücknimmt."),
    },
    "automatik": {
        "description": "Safari-Tabs regelmäßig automatisch aufräumen lassen",
        "text": (
            "Ich möchte, dass meine Safari-Tabs regelmäßig automatisch aufgeräumt werden. "
            "Antworte auf Deutsch.\n"
            "1. Rufe `safari_automatik_status` auf.\n"
            "2. Erkläre kurz: Die Automatik läuft im Hintergrund, nur wenn mein Mac eine Weile "
            "unbenutzt ist; sie schließt eindeutig überflüssige Tabs, speichert Tabs mit sicherer "
            "Zuordnung und ordnet alles: lose Lesezeichen kommen in thematische, verschachtelte "
            "Unterordner (breit → spezifisch, mindestens 2 Einträge, keine Sammelnamen), alle "
            "Ordner werden sortiert; meine eigenen Unterordner und die Reihenfolge meiner "
            "Hauptordner bleiben. Unsichere Tabs bleiben offen. Nach jedem Lauf gibt es eine "
            "Mitteilung und einen Bericht; jeder Lauf ist rückgängig machbar. Safari wird dafür "
            "kurz beendet.\n"
            "3. Zeig mir mit `safari_automatik_vorschau`, was der erste Lauf ordnen würde. Frag "
            "mich: monatlich (Standard), wöchentlich oder täglich? Gespeicherte Tabs danach "
            "schließen?\n"
            "4. Erst nach meinem OK `safari_automatik_einrichten` und sag mir, dass macOS gleich "
            "fragt, ob Python Safari steuern darf (erlauben)."),
    },
    "lesezeichen-korrigieren": {
        "description": "Falsch eingetragene Lesezeichen finden und entfernen",
        "text": (
            "Bei meinen Safari-Lesezeichen ist etwas falsch eingetragen. Antworte auf Deutsch.\n"
            "1. Rufe `safari_lesezeichen_verlauf` auf und zeig mir die letzten Änderungen "
            "(was wann in welchen Ordner kam).\n"
            "2. Frag mich, was falsch ist, oder finde es mit `safari_lesezeichen_suchen`.\n"
            "3. Zeig mir eine Liste (Titel, Ordner), was entfernt wird, und entferne es erst "
            "nach meinem OK mit `safari_lesezeichen_entfernen`.\n"
            "4. Biete an, die richtigen Einträge danach neu einzutragen.\n"
            "Eine Sicherung nur zurückspielen, wenn ich das ausdrücklich will."),
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
