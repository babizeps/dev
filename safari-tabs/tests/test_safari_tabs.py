import json
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


if __name__ == "__main__":
    unittest.main()
