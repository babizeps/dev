import json
import os
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import safari_tabs as st  # noqa: E402
from make_sample_plist import sample  # noqa: E402


def load_sample():
    data = json.loads((HERE / "sample_tabs.json").read_text(encoding="utf-8"))
    return [st.Tab(window=d["window"], index=d["index"], title=d["title"], url=d["url"]) for d in data]


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.cfg = st.load_config(None)
        self.plan = st.analyze(load_sample(), self.cfg)
        self.by = {t.num: t for t in self.plan.tabs}

    def test_actions(self):
        expected = {
            1: st.CLOSE, 2: st.BOOKMARK, 3: st.CLOSE, 4: st.CLOSE, 5: st.BOOKMARK,
            6: st.KEEP, 7: st.CLOSE, 8: st.BOOKMARK, 9: st.BOOKMARK, 10: st.CLOSE,
            11: st.CLOSE, 12: st.BOOKMARK, 13: st.BOOKMARK,
        }
        self.assertEqual({n: t.action for n, t in self.by.items()}, expected)

    def test_reasons(self):
        self.assertIn("Duplikat von #2", self.by[3].reason)
        self.assertIn("Duplikat von #9", self.by[10].reason)
        self.assertEqual(self.by[4].reason, "Suchergebnis")
        self.assertEqual(self.by[7].reason, "Login-/Anmeldeseite")
        self.assertEqual(self.by[11].reason, "Fehlerseite")

    def test_already_bookmarked_names_folder(self):
        bm = {st.normalize_url("https://de.wikipedia.org/wiki/Vulkan"): "Wissen"}
        t = st.analyze(load_sample(), self.cfg, bm).tabs[7]
        self.assertEqual((t.action, t.reason), (st.CLOSE, "schon gespeichert in Wissen"))

    def test_clean_url(self):
        self.assertEqual(st.clean_url("https://a.de/x?utm_source=1&id=5&fbclid=z",
                                      self.cfg["tracking_params"]), "https://a.de/x?id=5")


class FolderMatchTest(unittest.TestCase):
    def setUp(self):
        self.cfg = st.load_config(None)
        self.root = sample()
        self.folders = st.collect_folders(self.root)
        idx = st.bookmark_index(self.root, self.cfg["tracking_params"])
        self.plan = st.analyze(load_sample(), self.cfg, idx)
        st.assign_folders(self.plan, self.folders, self.cfg)
        self.by = {t.num: t for t in self.plan.tabs}

    def test_folders_collected_without_reading_list(self):
        paths = [f.path for f in self.folders]
        self.assertIn("Lesezeichenmenü/Programmieren/Python", paths)
        self.assertIn("Favoriten", paths)
        self.assertNotIn("com.apple.ReadingList", " ".join(paths))

    def test_reading_list_is_not_treated_as_bookmark(self):
        self.assertEqual(self.by[8].action, st.BOOKMARK)

    def test_assignments(self):
        self.assertEqual(self.by[2].target_path, "Favoriten")                       # github host
        self.assertEqual(self.by[5].target_path, "Lesezeichenmenü/Programmieren/Python")
        self.assertEqual(self.by[9].target_path, "Musik & Videos")                   # youtube
        self.assertEqual(self.by[12].target_path, "Kochen")                          # Thema Rezepte
        self.assertTrue(self.by[13].target_new)                                      # Blog
        self.assertEqual(self.by[13].target_path, "Unsortiert")
        self.assertTrue(self.by[8].target_new)                                       # Wikipedia

    def test_write_into_existing_folders(self):
        save = self.plan.by_action(st.BOOKMARK)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Bookmarks.plist"
            p.write_bytes(plistlib.dumps(self.root, fmt=plistlib.FMT_BINARY))
            result, backup = st.write_bookmarks_plist(save, self.cfg, p)
            self.assertTrue(backup.exists())
            self.assertEqual(result["Kochen"], 1)
            self.assertEqual(result["Unsortiert"], 2)
            new = plistlib.loads(p.read_bytes())
            kochen = next(c for c in new["Children"] if c.get("Title") == "Kochen")
            self.assertEqual(kochen["Children"][0]["URLString"],
                             "https://www.chefkoch.de/rezepte/123/lasagne.html")
            python = new["Children"][2]["Children"][0]["Children"][1]
            self.assertEqual(python["Title"], "Python")
            self.assertEqual(len(python["Children"]), 2)
            # zweiter Lauf fügt nichts doppelt hinzu
            result2, _ = st.write_bookmarks_plist(save, self.cfg, p)
            self.assertEqual(sum(result2.values()), 0)

    def test_manual_reassign_to_new_folder(self):
        t = self.by[13]
        st.set_new_target(t, "Blogs")
        save = self.plan.by_action(st.BOOKMARK)
        added = st.add_to_existing_folders(self.root, save, self.cfg)
        self.assertEqual(added["Blogs"], 1)

    def test_html_export(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "b.html"
            n = st.export_html(self.plan.by_action(st.BOOKMARK), self.cfg, out)
            self.assertEqual(n, 6)
            self.assertNotIn("utm_source", out.read_text(encoding="utf-8"))


class ContentTypeFoldersTest(unittest.TestCase):
    """Ordner nach Inhaltsart, wie Video / Book / Article / Tool / Event / Forum / AI-Chat / Shop."""

    CASES = [
        ("Lofi beats - YouTube", "https://www.youtube.com/watch?v=abc", "Video"),
        ("ChatGPT", "https://chatgpt.com/c/123", "AI-Chat"),
        ("Claude", "https://claude.ai/chat/abc", "AI-Chat"),
        ("Perplexity", "https://www.perplexity.ai/search/was-ist-xyz", "AI-Chat"),
        ("Atomic Habits | Goodreads", "https://www.goodreads.com/book/show/40121378", "Book"),
        ("Clean Code: Buch", "https://www.thalia.de/shop/home/artikeldetails/A1", "Book"),
        ("Vulkane - SPIEGEL", "https://www.spiegel.de/wissenschaft/vulkane-a-1.html", "Article"),
        ("Blogpost", "https://blog.example.org/2025/03/mein-erster-beitrag", "Article"),
        ("regex101", "https://regex101.com/", "Tool"),
        ("anthropics/claude-code", "https://github.com/anthropics/claude-code", "Tool"),
        ("Bug · Issue #12", "https://github.com/foo/bar/issues/12", "Forum"),
        ("r/macapps", "https://www.reddit.com/r/macapps/comments/abc/t/", "Forum"),
        ("Tech Meetup", "https://www.meetup.com/berlin-tech/events/123/", "Event"),
        ("Konzert Tickets", "https://www.eventim.de/event/konzert-123/", "Event"),
        ("AirPods Pro", "https://www.amazon.de/Apple-AirPods-Pro/dp/B0CHWRXH8B", "Shop"),
    ]

    def test_kind_folders(self):
        from make_sample_plist import folder
        names = ["Video", "Book", "Article", "Tool", "Event", "Forum", "AI-Chat", "Shop"]
        root = {"Children": [folder("BookmarksBar", []),
                             folder("BookmarksMenu", [folder(n, []) for n in names])]}
        cfg = st.load_config(None)
        tabs = [st.Tab(1, i + 1, t, u) for i, (t, u, _) in enumerate(self.CASES)]
        plan = st.analyze(tabs, cfg, {})
        st.assign_folders(plan, st.collect_folders(root), cfg)
        for tab, (_, _, want) in zip(plan.tabs, self.CASES):
            self.assertEqual(tab.target_path, "Lesezeichenmenü/" + want, tab.title)


class CloudTabsTest(unittest.TestCase):
    def setUp(self):
        from make_sample_cloudtabs import make
        self.dir = tempfile.TemporaryDirectory()
        self.db = Path(self.dir.name) / "CloudTabs.db"
        make(str(self.db))

    def tearDown(self):
        self.dir.cleanup()

    def test_read_and_exclude_this_mac(self):
        tabs, devices = st.read_cloud_tabs(self.db, exclude_devices=["MacBook Air"])
        self.assertEqual([t.title for t in tabs][:2], ["ChatGPT", "Atomic Habits | Goodreads"])
        self.assertEqual(len(tabs), 4)
        self.assertTrue(all(t.device == "iPhone von Jürgen" and t.remote for t in tabs))
        self.assertEqual(devices[0]["geraet"], "iPhone von Jürgen")
        self.assertEqual(devices[0]["tabs"], 4)
        self.assertTrue(devices[0]["zuletzt_synchronisiert"])

    def test_mixed_with_mac_tabs(self):
        remote, _ = st.read_cloud_tabs(self.db, exclude_devices=["MacBook Air"])
        mac = [st.Tab(1, 1, "Lofi beats - YouTube", "https://www.youtube.com/watch?v=abc")]
        cfg = st.load_config(None)
        plan = st.analyze(mac + remote, cfg, {})
        by = {t.title: t for t in plan.tabs[1:]}
        self.assertEqual(by["Lofi beats - YouTube"].reason, "auch am Mac offen (#1)")
        self.assertEqual(by["pizza in der nähe - Google Suche"].action, st.CLOSE)
        self.assertEqual(by["ChatGPT"].action, st.BOOKMARK)

    def test_missing_db(self):
        with self.assertRaises(FileNotFoundError):
            st.read_cloud_tabs(Path(self.dir.name) / "nope.db")


class TerminalBridgeTest(unittest.TestCase):
    """Umweg über Terminal: 'open -a Terminal x.command' wird hier nachgestellt."""

    def setUp(self):
        from make_sample_plist import sample
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.saved = (st.BRIDGE_DIR, st.BOOKMARKS_PLIST, st.CLOUD_TABS_DBS, st.subprocess.run)
        st.BRIDGE_DIR = base / "bridge"
        st.BOOKMARKS_PLIST = base / "Safari" / "Bookmarks.plist"
        st.BOOKMARKS_PLIST.parent.mkdir()
        st.BOOKMARKS_PLIST.write_bytes(plistlib.dumps(sample(), fmt=plistlib.FMT_BINARY))
        st.CLOUD_TABS_DBS = [base / "Safari" / "CloudTabs.db"]
        from make_sample_cloudtabs import make
        make(str(st.CLOUD_TABS_DBS[0]))
        self.opened = []

        def fake_run(cmd, *a, **k):
            if cmd[:3] == ["open", "-a", "Terminal"]:
                self.opened.append(cmd[3])
                text = Path(cmd[3]).read_text(encoding="utf-8")
                op = text.split("--bridge-op ")[1].split()[0]
                token = text.split("--bridge-token ")[1].split()[0]
                st.bridge_main(op, token)          # „Terminal“ führt das Skript aus
                return None
            return self.saved[3](cmd, *a, **k)
        st.subprocess.run = fake_run

    def tearDown(self):
        st.BRIDGE_DIR, st.BOOKMARKS_PLIST, st.CLOUD_TABS_DBS, st.subprocess.run = self.saved
        self.tmp.cleanup()

    def test_copy_then_apply(self):
        root = None
        res = st.run_via_terminal("copy")
        self.assertTrue(res["cloud"])
        root = st.load_bookmarks(st.BRIDGE_DIR / "Bookmarks.plist")
        self.assertTrue(st.collect_folders(root))
        cloud = st.BRIDGE_DIR / "cloud" / "CloudTabs.db"
        tabs, _ = st.read_cloud_tabs(cloud)
        self.assertEqual(len(tabs), 5)
        st.cleanup_bridge_copies()
        self.assertFalse((st.BRIDGE_DIR / "Bookmarks.plist").exists())
        self.assertFalse(cloud.exists())

        t = st.Tab(0, 0, "Lasagne", "https://www.chefkoch.de/rezepte/1/lasagne.html")
        st.set_new_target(t, "Kochen")
        res = st.run_via_terminal("edit", {"add": [st._tab_to_dict(t)]})
        self.assertEqual(res["ergebnis"], {"Kochen": 1})
        self.assertEqual(len(res["hinzugefuegt"]), 1)
        listed = st.run_via_terminal("list")["sicherungen"]
        self.assertTrue(listed[0]["name"].startswith("Bookmarks.plist.backup-"))
        new = plistlib.loads(st.BOOKMARKS_PLIST.read_bytes())
        kochen = next(c for c in new["Children"] if c.get("Title") == "Kochen")
        self.assertEqual(len(kochen["Children"]), 1)
        self.assertTrue(list(st.BOOKMARKS_PLIST.parent.glob("Bookmarks.plist.backup-*")))
        # Skript ruft dieselbe Python-Datei auf, Austauschdateien sind aufgeräumt
        self.assertIn(str(Path(st.__file__).resolve()), Path(self.opened[0]).read_text())
        self.assertEqual(list(st.BRIDGE_DIR.glob("*.*.json")), [])

    def test_terminal_without_access_reports_hint(self):
        orig = st.shutil.copy2

        def denied(*a, **k):
            raise PermissionError(1, "Operation not permitted")
        st.shutil.copy2 = denied
        try:
            with self.assertRaises(st.BridgeError) as cm:
                st.run_via_terminal("copy")
            self.assertIn("Festplattenvollzugriff", str(cm.exception))
            self.assertIn("Terminal", str(cm.exception))
        finally:
            st.shutil.copy2 = orig

class CorrectionTest(unittest.TestCase):
    """Entfernen, rückgängig machen, Sicherung zurückspielen."""

    def setUp(self):
        from make_sample_plist import sample, folder, leaf
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.saved = st.BRIDGE_DIR
        st.BRIDGE_DIR = base / "bridge"
        self.path = base / "Bookmarks.plist"
        root = {"Children": [folder("BookmarksBar", []), folder("BookmarksMenu", [
            folder("Video", [leaf("https://www.youtube.com/watch?v=ok", "Gutes Video")]),
            folder("Article", [leaf("https://example.com/a", "Artikel A")]),
            folder("Tool", [leaf("https://example.com/a", "Gleiche URL im Tool-Ordner")]),
        ])]}
        self.path.write_bytes(plistlib.dumps(root, fmt=plistlib.FMT_BINARY))
        self.cfg = st.load_config(None)

    def tearDown(self):
        st.BRIDGE_DIR = self.saved
        self.tmp.cleanup()

    def root(self):
        return plistlib.loads(self.path.read_bytes())

    def urls_in(self, name):
        return [h["url"] for h in st.search_bookmarks(self.root(), "", name)]

    def add(self, items):
        tabs = []
        for title, url, target, new in items:
            t = st.Tab(0, 0, title, url)
            if new:
                st.set_new_target(t, target)
            else:
                t.target_key, t.target_path = "", "Lesezeichenmenü/" + target
            tabs.append(st._tab_to_dict(t))
        return st.edit_bookmarks({"add": tabs, "aktion": "Test"}, self.path)

    def test_undo_last_save_removes_only_its_bookmarks(self):
        self.add([("Spy", "https://www.youtube.com/watch?v=spy", "Video", False),
                  ("WSJ", "https://wsj.com/ai", "Article", False),
                  ("Neu", "https://neu.example/", "Testordner", True)])
        self.assertEqual(len(self.urls_in("Video")), 2)
        entry = st.last_undoable()
        self.assertEqual(len(entry["hinzugefuegt"]), 3)
        res = st.edit_bookmarks(st.undo_change_for(entry), self.path)
        st.mark_undone(entry)
        self.assertEqual(len(res["entfernt"]), 3)
        self.assertEqual(self.urls_in("Video"), ["https://www.youtube.com/watch?v=ok"])
        self.assertEqual(self.urls_in("Article"), ["https://example.com/a"])
        titles = [c.get("Title") for c in self.root()["Children"]]
        self.assertNotIn("Testordner", titles)             # leerer, neu angelegter Ordner weg
        self.assertIsNone(st.last_undoable())

    def test_remove_by_url_only_in_given_folder(self):
        res = st.edit_bookmarks({"remove": [{"url": "https://example.com/a",
                                             "ordner": "Article"}]}, self.path)
        self.assertEqual(len(res["entfernt"]), 1)
        self.assertEqual(self.urls_in("Article"), [])
        self.assertEqual(self.urls_in("Tool"), ["https://example.com/a"])

    def test_remove_by_title_and_folder(self):
        res = st.edit_bookmarks({"remove": [{"titel": "gutes video", "ordner": "Video"}]},
                                self.path)
        self.assertEqual([r["titel"] for r in res["entfernt"]], ["Gutes Video"])
        self.assertTrue(list(self.path.parent.glob("Bookmarks.plist.backup-*")))

    def test_existing_folders_are_never_removed(self):
        video_id = next(c for c in self.root()["Children"][1]["Children"]
                        if c["Title"] == "Video")["WebBookmarkUUID"]
        st.edit_bookmarks({"remove": [{"titel": "Gutes Video", "ordner": "Video"}],
                           "remove_folder_ids": []}, self.path)
        self.assertIn("Video", [c["Title"] for c in self.root()["Children"][1]["Children"]])
        self.assertTrue(video_id)

    def test_restore_backup(self):
        before = self.path.read_bytes()
        res = self.add([("Spy", "https://www.youtube.com/watch?v=spy", "Video", False)])
        backup = res["sicherung"]
        import time as _t
        _t.sleep(1.1)                                       # anderer Zeitstempel
        r = st.edit_bookmarks({"restore": backup}, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(r["sicherung"].startswith("Bookmarks.plist.vor-wiederherstellung-"))
        self.assertTrue((self.path.parent / r["sicherung"]).exists())
        names = [b["name"] for b in st.list_backups(self.path)]
        self.assertIn(backup, names)

    def test_subfolders_created_inside_existing_and_undone(self):
        folders = st.collect_folders(self.root())
        f, new = st.resolve_target("Video/Musik/Live", folders)
        self.assertIsNone(f)
        self.assertEqual(new, "Lesezeichenmenü/Video/Musik/Live")
        t = st.Tab(0, 0, "Konzert", "https://www.youtube.com/watch?v=live")
        st.set_new_target(t, new)
        entry = st.edit_bookmarks({"add": [st._tab_to_dict(t)]}, self.path)
        self.assertEqual([o["titel"] for o in entry["ordner_neu"]],
                         ["Lesezeichenmenü/Video/Musik", "Lesezeichenmenü/Video/Musik/Live"])
        self.assertEqual(self.urls_in("Lesezeichenmenü/Video/Musik/Live"),
                         ["https://www.youtube.com/watch?v=live"])
        # zweiter Eintrag in denselben (jetzt vorhandenen) Unterordner
        folders = st.collect_folders(self.root())
        f, new = st.resolve_target("Musik/Live", folders)
        self.assertEqual(f.path, "Lesezeichenmenü/Video/Musik/Live")
        # rückgängig: Lesezeichen und beide neuen (leeren) Ordner weg, Video bleibt
        st.edit_bookmarks(st.undo_change_for(st.last_undoable()), self.path)
        video = next(c for c in self.root()["Children"][1]["Children"] if c["Title"] == "Video")
        self.assertEqual([c.get("Title") for c in video["Children"]
                          if c.get("WebBookmarkType") == "WebBookmarkTypeList"], [])
        self.assertEqual(self.urls_in("Video"), ["https://www.youtube.com/watch?v=ok"])

    def test_ambiguous_subfolder_name(self):
        from make_sample_plist import folder
        folders = [st.Folder(key="a", path="Lesezeichenmenü/Video/Musik", title="Musik", depth=2),
                   st.Folder(key="b", path="Lesezeichenmenü/Book/Musik", title="Musik", depth=2)]
        with self.assertRaises(st.AmbiguousFolder):
            st.resolve_target("Musik", folders)
        f, _ = st.resolve_target("Book/Musik", folders)
        self.assertEqual(f.key, "b")
        self.assertTrue(folder)

    def test_restore_rejects_bad_names(self):
        for bad in ("../../etc/passwd", "Bookmarks.plist", "Bookmarks.plist.backup-x"):
            with self.assertRaises(ValueError):
                st.edit_bookmarks({"restore": bad}, self.path)


if __name__ == "__main__":
    unittest.main()
