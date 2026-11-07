"""Simuliert eine MCP-Sitzung der Claude-App mit nachgebildetem Safari."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "claude-app"))
sys.path.insert(0, str(HERE))

import safari_tabs as st  # noqa: E402
import server  # noqa: E402
from make_sample_plist import folder, leaf  # noqa: E402

FOLDERS = ["Video", "Book", "Article", "Tool", "Event", "Forum", "AI-Chat", "Shop"]
TABS = [
    ("Favoriten", "favorites://"),
    ("Lofi beats - YouTube", "https://www.youtube.com/watch?v=abc"),
    ("Lofi beats - YouTube", "https://m.youtube.com/watch?v=abc"),
    ("ChatGPT", "https://chatgpt.com/c/1"),
    ("python sort - Google Suche", "https://www.google.com/search?q=python+sort"),
    ("Restaurant Luigi", "https://luigi-restaurant.de/"),
]


class FakeSafari:
    def __init__(self):
        self.tabs = [st.Tab(1, i + 1, t, u) for i, (t, u) in enumerate(TABS)]
        self.root = {"Children": [folder("BookmarksBar", []), folder("BookmarksMenu", [
            folder(n, [leaf("https://www.youtube.com/@x", "x")] if n == "Video" else [])
            for n in FOLDERS])]}
        self.saved = None

    def read(self):
        return [st.Tab(1, i + 1, t.title, t.url) for i, t in enumerate(self.tabs)]

    def remote(self):
        return [st.Tab(0, 0, "Atomic Habits | Goodreads",
                       "https://www.goodreads.com/book/show/1", device="iPhone"),
                st.Tab(0, 0, "pizza - Google Suche", "https://www.google.com/search?q=pizza",
                       device="iPhone")]

    def close(self, tabs):
        assert not any(t.remote for t in tabs), "iPhone-Tabs dürfen nicht an Safari gehen"
        urls = [t.url for t in tabs]
        before = len(self.tabs)
        for u in urls:
            for i, t in enumerate(self.tabs):
                if t.url == u:
                    del self.tabs[i]
                    break
        return {"closed": before - len(self.tabs), "skipped": 0}

    def save(self, tabs, cfg, via_terminal=False):
        self.saved = st.add_to_existing_folders(self.root, tabs, cfg)
        print("★ gespeichert")
        return True


class ServerSessionTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSafari()
        self._orig = (st.read_safari_tabs, st.close_tabs, st.load_bookmarks, st.save_into_safari)
        st.read_safari_tabs = self.fake.read
        self._orig_all = st.read_all_tabs
        st.read_all_tabs = lambda include_cloud=True, cloud_db=None: (
            self.fake.read() + (self.fake.remote() if include_cloud else []),
            [{"geraet": "iPhone", "tabs": 2}] if include_cloud else [], None)
        st.close_tabs = self.fake.close
        st.load_bookmarks = lambda *a, **k: self.fake.root
        self._orig_any = st.load_bookmarks_any
        st.load_bookmarks_any = lambda allow_terminal=True: (self.fake.root, "direkt", None)
        st.save_into_safari = self.fake.save
        server.STATE.update(plan=None, folders=[], cfg=None)

    def tearDown(self):
        st.read_safari_tabs, st.close_tabs, st.load_bookmarks, st.save_into_safari = self._orig
        st.read_all_tabs = self._orig_all
        st.load_bookmarks_any = self._orig_any

    def rpc(self, lines):
        out = io.StringIO()
        server.OUT = out
        sys.stdin, old = io.StringIO("\n".join(json.dumps(l) for l in lines) + "\n"), sys.stdin
        try:
            server.main()
        finally:
            sys.stdin = old
        return [json.loads(l) for l in out.getvalue().splitlines()]

    def call(self, i, name, args=None):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": name, "arguments": args or {}}}

    def test_full_session(self):
        res = self.rpc([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "claude-ai", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "prompts/list"},
            {"jsonrpc": "2.0", "id": 4, "method": "prompts/get",
             "params": {"name": "tabs-aufraeumen"}},
            self.call(5, "safari_tabs_ueberblick"),
        ])
        self.assertEqual([r["id"] for r in res], [1, 2, 3, 4, 5])
        self.assertEqual(res[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(len(res[1]["result"]["tools"]), 9)
        self.assertEqual([p["name"] for p in res[2]["result"]["prompts"]],
                         ["tabs-aufraeumen", "unterordner-erstellen", "lesezeichen-korrigieren"])
        self.assertIn("safari_tabs_ueberblick",
                      res[3]["result"]["messages"][0]["content"]["text"])
        ov = json.loads(res[4]["result"]["content"][0]["text"])
        self.assertEqual(ov["zusammenfassung"]["schliessen"], 4)
        self.assertEqual(ov["zusammenfassung"]["mac_tabs"], 6)

        self.assertEqual(ov["tabs"][6]["geraet"], "iPhone")
        self.assertEqual(ov["tabs"][6]["ordner_vorschlag"], "Lesezeichenmenü/Book")
        by = {t["nr"]: t for t in ov["tabs"]}
        self.assertEqual(by[2]["ordner_vorschlag"], "Lesezeichenmenü/Video")
        self.assertEqual(by[4]["ordner_vorschlag"], "Lesezeichenmenü/AI-Chat")
        self.assertEqual(len(ov["ordner"]), 10)

        res = self.rpc([
            self.call(6, "safari_tabs_schliessen", {"nummern": [1, 3, 5, 8]}),
            self.call(7, "safari_lesezeichen_speichern", {"eintraege": [
                {"nummer": 2, "ordner": "Video"},
                {"nummer": 4, "ordner": "Lesezeichenmenü/AI-Chat"},
                {"nummer": 6, "ordner": "Restaurants"},
                {"nummer": 7, "ordner": "Book"},
            ]}),
        ])
        closed = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertEqual(closed["geschlossen"], 3)
        self.assertEqual([t["nr"] for t in closed["selbst_schliessen"]], [8])
        self.assertEqual(len(self.fake.tabs), 3)
        saved = json.loads(res[1]["result"]["content"][0]["text"])
        self.assertTrue(saved["ok"])
        self.assertEqual(self.fake.saved, {"Lesezeichenmenü/Video": 1,
                                           "Lesezeichenmenü/AI-Chat": 1,
                                           "Lesezeichenmenü/Book": 1})
        self.assertIn("Restaurants", saved["probleme"][0])   # neuer Ordner nicht erlaubt
        self.assertIsNone(server.STATE["plan"])

    def test_new_folder_when_allowed(self):
        self.rpc([self.call(1, "safari_tabs_ueberblick")])
        res = self.rpc([self.call(2, "safari_lesezeichen_speichern", {
            "eintraege": [{"nummer": 6, "ordner": "Restaurants"}],
            "neue_ordner_erlaubt": True})])
        out = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertEqual(out["neue_ordner"], ["Restaurants"])
        self.assertEqual(self.fake.saved, {"Restaurants": 1})

    def test_tool_needs_overview_first(self):
        res = self.rpc([self.call(1, "safari_tabs_schliessen", {"nummern": [1]})])
        self.assertTrue(res[0]["result"]["isError"])

    def test_safari_error_is_reported(self):
        def boom(include_cloud=True, cloud_db=None):
            raise SystemExit("Kein Zugriff auf Safari. Terminal → Safari")
        st.read_all_tabs = boom
        res = self.rpc([self.call(1, "safari_tabs_ueberblick")])
        self.assertTrue(res[0]["result"]["isError"])
        self.assertIn("Claude → Safari", res[0]["result"]["content"][0]["text"])

    def test_no_bookmark_access_gives_diagnosis(self):
        st.load_bookmarks_any = lambda allow_terminal=True: (None, "", None)
        res = self.rpc([self.call(1, "safari_tabs_ueberblick"),
                        self.call(2, "safari_zugriff_pruefen")])
        ov = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertFalse(ov["lesezeichen_zugriff"])
        self.assertIn("Terminal", ov["hinweis"])
        diag = json.loads(res[1]["result"]["content"][0]["text"])
        self.assertIn(diag["python_programm"], diag["anleitung"][1])
        self.assertFalse(diag["alles_ok"])

    def test_python_app_from_framework_path(self):
        path = ("/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/"
                "Versions/3.9/Resources/Python.app/Contents/MacOS/Python")
        self.assertEqual(st._app_bundle(path), path.split("/Contents/")[0])

    def test_undo_and_remove_via_tools(self):
        import plistlib, tempfile
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        saved = (st.BRIDGE_DIR, st.BOOKMARKS_PLIST, st.apply_bookmark_change)
        try:
            st.BRIDGE_DIR = base / "bridge"
            st.BOOKMARKS_PLIST = base / "Bookmarks.plist"
            st.BOOKMARKS_PLIST.write_bytes(plistlib.dumps(self.fake.root, fmt=plistlib.FMT_BINARY))
            st.apply_bookmark_change = lambda change, via_terminal=None: {
                "ok": True, **st.edit_bookmarks(change, st.BOOKMARKS_PLIST)}
            st.load_bookmarks_any = lambda allow_terminal=True: (
                plistlib.loads(st.BOOKMARKS_PLIST.read_bytes()), "direkt", None)
            # falsch eintragen
            t1 = st.Tab(0, 0, "How I Caught a Spy", "https://www.youtube.com/watch?v=spy")
            t1.target_path = "Lesezeichenmenü/Video"
            t2 = st.Tab(0, 0, "The AI Future – WSJ", "https://www.wsj.com/ai")
            t2.target_path = "Lesezeichenmenü/Article"
            st.edit_bookmarks({"add": [st._tab_to_dict(t1), st._tab_to_dict(t2)]},
                              st.BOOKMARKS_PLIST)
            res = self.rpc([
                self.call(1, "safari_lesezeichen_verlauf"),
                self.call(2, "safari_lesezeichen_suchen", {"suche": "wsj"}),
                self.call(3, "safari_lesezeichen_entfernen", {"eintraege": [
                    {"titel": "The AI Future – WSJ", "ordner": "Article"}]}),
                self.call(4, "safari_lesezeichen_entfernen",
                          {"letzte_speicherung_rueckgaengig": True}),
                self.call(5, "safari_lesezeichen_suchen", {"suche": "", "ordner": "Video"}),
                self.call(6, "safari_sicherung_zurueckspielen", {"sicherung": "../x"}),
            ])
            j = [json.loads(r["result"]["content"][0]["text"]) if not r["result"].get("isError")
                 else r["result"] for r in res]
            self.assertEqual(len(j[0]["aenderungen"][0]["hinzugefuegt"]), 2)
            self.assertTrue(j[0]["sicherungen"])
            self.assertEqual(j[1]["treffer"][0]["ordner"], "Lesezeichenmenü/Article")
            self.assertEqual(len(j[2]["entfernt"]), 1)
            self.assertIn("iCloud", j[2]["hinweis"])
            self.assertEqual([e["titel"] for e in j[3]["entfernt"]], ["How I Caught a Spy"])
            self.assertEqual([h["titel"] for h in j[4]["treffer"]], ["x"])  # nur das alte bleibt
            self.assertTrue(j[5]["isError"])
            self.assertIn("Ungültiger Sicherungsname", j[5]["content"][0]["text"])
        finally:
            st.BRIDGE_DIR, st.BOOKMARKS_PLIST, st.apply_bookmark_change = saved
            tmp.cleanup()

    def test_subfolder_suggestion_and_save(self):
        self.fake.tabs = [st.Tab(1, i + 1, t, u) for i, (t, u) in enumerate([
            ("Lofi beats to study - YouTube", "https://www.youtube.com/watch?v=1"),
            ("Jazz lofi mix - YouTube", "https://www.youtube.com/watch?v=2"),
            ("Python tutorial for beginners", "https://www.youtube.com/watch?v=3"),
            ("Advanced python decorators", "https://vimeo.com/123"),
        ])]
        res = self.rpc([self.call(1, "safari_tabs_ueberblick", {"andere_geraete": False}),
                        self.call(2, "safari_unterordner_vorschlagen")])
        hints = json.loads(res[1]["result"]["content"][0]["text"])["ordner"]
        video = next(h for h in hints if h["ordner"] == "Lesezeichenmenü/Video")
        self.assertEqual(len(video["tabs"]), 4)
        self.assertEqual(video["gemeinsame_seiten"]["youtube.com"], [1, 2, 3])
        self.assertEqual(video["haeufige_woerter"]["lofi"], [1, 2])
        self.assertEqual(video["haeufige_woerter"]["python"], [3, 4])

        res = self.rpc([
            self.call(3, "safari_lesezeichen_speichern", {"eintraege": [
                {"nummer": 1, "ordner": "Video/Musik"}]}),
        ])
        out = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertIn("neue_ordner_erlaubt", out["probleme"][0])
        self.rpc([self.call(4, "safari_tabs_ueberblick", {"andere_geraete": False})])
        res = self.rpc([
            self.call(5, "safari_lesezeichen_speichern", {"neue_ordner_erlaubt": True,
                                                          "eintraege": [
                {"nummer": 1, "ordner": "Video/Musik"},
                {"nummer": 2, "ordner": "Video/Musik"},
                {"nummer": 3, "ordner": "Video/Programmieren"}]}),
        ])
        out = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertEqual(out["neue_ordner"], ["Lesezeichenmenü/Video/Musik",
                                              "Lesezeichenmenü/Video/Programmieren"])
        self.assertEqual(self.fake.saved, {"Lesezeichenmenü/Video/Musik": 2,
                                           "Lesezeichenmenü/Video/Programmieren": 1})
        menu = self.fake.root["Children"][1]["Children"]
        video_node = next(c for c in menu if c["Title"] == "Video")
        subs = [c["Title"] for c in video_node["Children"]
                if c.get("WebBookmarkType") == "WebBookmarkTypeList"]
        self.assertEqual(subs, ["Musik", "Programmieren"])
        self.assertEqual(sum(1 for c in menu if c["Title"] == "Video"), 1)

    def test_unknown_method(self):
        res = self.rpc([{"jsonrpc": "2.0", "id": 9, "method": "foo/bar"}])
        self.assertEqual(res[0]["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
