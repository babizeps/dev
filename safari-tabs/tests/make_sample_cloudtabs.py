"""Erzeugt eine Beispiel-CloudTabs.db (Aufbau wie in Safari auf macOS)."""
import sqlite3
import sys


def make(path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE cloud_tab_devices (device_uuid TEXT PRIMARY KEY, system_fields BLOB,
        device_name TEXT, has_duplicate_device_name BOOLEAN, is_ephemeral_device BOOLEAN,
        last_modified REAL);
    CREATE TABLE cloud_tabs (tab_uuid TEXT PRIMARY KEY, system_fields BLOB, device_uuid TEXT,
        position BLOB, title TEXT, url TEXT, is_showing_reader BOOLEAN, is_pinned BOOLEAN,
        reader_scroll_position_page_index INTEGER, scene_id TEXT);
    CREATE TABLE cloud_tab_close_requests (close_request_uuid TEXT PRIMARY KEY,
        system_fields BLOB, destination_device_uuid TEXT, url TEXT, tab_uuid TEXT);
    """)
    con.executemany("INSERT INTO cloud_tab_devices (device_uuid, device_name, last_modified) "
                    "VALUES (?,?,?)", [
                        ("D1", "iPhone von Jürgen", 784000000.0),
                        ("D2", "MacBook Air", 784000000.0),
                    ])
    con.executemany("INSERT INTO cloud_tabs (tab_uuid, device_uuid, position, title, url) "
                    "VALUES (?,?,?,?,?)", [
                        ("T1", "D1", b"1", "ChatGPT", "https://chatgpt.com/c/1"),
                        ("T2", "D1", b"2", "Atomic Habits | Goodreads",
                         "https://www.goodreads.com/book/show/40121378"),
                        ("T3", "D1", b"3", "pizza in der nähe - Google Suche",
                         "https://www.google.com/search?q=pizza"),
                        ("T4", "D1", b"4", "Lofi beats - YouTube",
                         "https://m.youtube.com/watch?v=abc"),
                        ("T5", "D2", b"1", "Mac-Tab", "https://example.org/mac"),
                    ])
    con.commit()
    con.close()


if __name__ == "__main__":
    make(sys.argv[1])
