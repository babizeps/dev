"""Erzeugt eine Beispiel-Bookmarks.plist mit typischen Ordnern (für Tests)."""
import plistlib
import sys
import uuid


def leaf(url, title):
    return {"WebBookmarkType": "WebBookmarkTypeLeaf", "URLString": url,
            "URIDictionary": {"title": title}, "WebBookmarkUUID": str(uuid.uuid4()).upper()}


def folder(title, children):
    return {"WebBookmarkType": "WebBookmarkTypeList", "Title": title,
            "WebBookmarkUUID": str(uuid.uuid4()).upper(), "Children": children}


def sample():
    return {
        "WebBookmarkType": "WebBookmarkTypeList", "Title": "", "Children": [
            {"WebBookmarkType": "WebBookmarkTypeProxy", "Title": "History"},
            folder("BookmarksBar", [leaf("https://github.com/", "GitHub")]),
            folder("BookmarksMenu", [
                folder("Programmieren", [
                    leaf("https://stackoverflow.com/", "Stack Overflow"),
                    folder("Python", [leaf("https://docs.python.org/3/library/", "Python Library")]),
                ]),
            ]),
            folder("Kochen", []),
            folder("Musik & Videos", [leaf("https://www.youtube.com/@channel", "Kanal")]),
            folder("Reisen", [leaf("https://www.bahn.de/", "Bahn")]),
            folder("com.apple.ReadingList", [leaf("https://de.wikipedia.org/wiki/Vulkan", "x")]),
        ],
    }


if __name__ == "__main__":
    with open(sys.argv[1], "wb") as fh:
        plistlib.dump(sample(), fh, fmt=plistlib.FMT_BINARY)
