import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import safari_tabs as st  # noqa: E402


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
        got = {n: t.action for n, t in self.by.items()}
        self.assertEqual(got, expected)

    def test_reasons_and_categories(self):
        self.assertIn("Duplikat von #2", self.by[3].reason)
        self.assertIn("Duplikat von #9", self.by[10].reason)
        self.assertEqual(self.by[4].reason, "Suchergebnis")
        self.assertEqual(self.by[7].reason, "Login-/Anmeldeseite")
        self.assertEqual(self.by[11].reason, "Fehlerseite")
        self.assertEqual(self.by[2].category, "Entwicklung")
        self.assertEqual(self.by[5].category, "Entwicklung")
        self.assertEqual(self.by[8].category, "Wissen & Lernen")
        self.assertEqual(self.by[9].category, "Videos")
        self.assertEqual(self.by[12].category, "Rezepte")
        self.assertEqual(self.by[13].category, "Sonstiges")

    def test_already_bookmarked(self):
        bm = {st.normalize_url("https://de.wikipedia.org/wiki/Vulkan")}
        plan = st.analyze(load_sample(), self.cfg, bm)
        t = plan.tabs[7]
        self.assertEqual((t.action, t.reason), (st.CLOSE, "schon als Lesezeichen gespeichert"))

    def test_clean_url(self):
        self.assertEqual(st.clean_url("https://a.de/x?utm_source=1&id=5&fbclid=z", self.cfg["tracking_params"]),
                         "https://a.de/x?id=5")


class BookmarkWriteTest(unittest.TestCase):
    def test_plist_roundtrip_and_no_duplicates(self):
        cfg = st.load_config(None)
        plan = st.analyze(load_sample(), cfg)
        save = plan.by_action(st.BOOKMARK)
        root = {"Children": [
            {"WebBookmarkType": "WebBookmarkTypeList", "Title": "BookmarksBar", "Children": []},
            {"WebBookmarkType": "WebBookmarkTypeList", "Title": "BookmarksMenu", "Children": [
                {"WebBookmarkType": "WebBookmarkTypeLeaf", "URLString": "https://docs.python.org/3/howto/sorting.html",
                 "URIDictionary": {"title": "x"}}]},
        ], "WebBookmarkType": "WebBookmarkTypeList", "Title": ""}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Bookmarks.plist"
            p.write_bytes(plistlib.dumps(root, fmt=plistlib.FMT_BINARY))
            added, backup = st.write_bookmarks_plist(save, cfg, p)
            self.assertTrue(backup.exists())
            self.assertEqual(added, len(save) - 1)  # python docs already present
            new = plistlib.loads(p.read_bytes())
            self.assertEqual(new["Children"][2]["Title"], "Tab-Archiv")
            # second run adds nothing
            added2, _ = st.write_bookmarks_plist(save, cfg, p)
            self.assertEqual(added2, 0)

    def test_html_export(self):
        cfg = st.load_config(None)
        plan = st.analyze(load_sample(), cfg)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "b.html"
            n = st.export_html(plan.by_action(st.BOOKMARK), cfg, out)
            text = out.read_text(encoding="utf-8")
            self.assertEqual(n, 6)
            self.assertIn("<H3", text)
            self.assertIn("Entwicklung", text)
            self.assertNotIn("utm_source", text)


if __name__ == "__main__":
    unittest.main()
