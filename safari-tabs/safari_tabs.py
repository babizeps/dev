#!/usr/bin/env python3
"""safari-tabs – räumt Safari-Tabs auf.

Liest alle offenen Safari-Tabs, sortiert unnötige aus (Duplikate, leere Tabs,
Suchergebnisse, Login-Seiten, Fehlerseiten, bereits gespeicherte Seiten …),
schließt sie und legt die wichtigen geordnet nach Kategorien als Lesezeichen ab.

Nur Python-Standardbibliothek, läuft mit dem macOS-eigenen python3 (>= 3.8).
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import html
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BOOKMARKS_PLIST = Path.home() / "Library" / "Safari" / "Bookmarks.plist"

CLOSE = "close"
BOOKMARK = "bookmark"
KEEP = "keep"

ACTION_LABEL = {CLOSE: "schließen", BOOKMARK: "Lesezeichen", KEEP: "behalten"}
ACTION_KEY = {"s": CLOSE, "l": BOOKMARK, "b": KEEP}

# --------------------------------------------------------------------------
# Standard-Konfiguration (kann per --config JSON-Datei überschrieben werden)
# --------------------------------------------------------------------------
DEFAULT_CONFIG: Dict = {
    "folder": "Tab-Archiv",
    "close_already_bookmarked": True,
    "close_search_results": True,
    "close_auth_pages": True,
    "close_error_pages": True,
    # Tracking-Parameter, die beim Duplikat-Vergleich ignoriert und beim
    # Speichern entfernt werden
    "tracking_params": [
        "utm_*", "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
        "igshid", "si", "ref", "ref_src", "_hsenc", "_hsmi", "spm",
    ],
    # Seiten, die offen bleiben sollen, aber nicht als Lesezeichen taugen
    # (Web-Apps, Postfächer …). Reguläre Ausdrücke auf die URL.
    "keep_open_patterns": [
        r"^https?://mail\.google\.com/",
        r"^https?://calendar\.google\.com/",
        r"^https?://(outlook\.live|outlook\.office|outlook\.office365)\.com/",
        r"^https?://web\.whatsapp\.com/",
        r"^https?://web\.telegram\.org/",
        r"^https?://app\.slack\.com/",
        r"^https?://(www\.)?icloud\.com/(mail|calendar)",
        r"^https?://music\.(apple|youtube)\.com/",
        r"^https?://open\.spotify\.com/",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?/",
    ],
    # Eigene Regeln: immer schließen / immer als Lesezeichen sichern
    "close_patterns": [],
    "bookmark_patterns": [],
    # Kategorien → Domains (Suffix-Match auf den Hostnamen) oder
    # reguläre Ausdrücke (mit "re:" davor) auf die komplette URL.
    # Reihenfolge = Priorität. Nicht zugeordnete Tabs landen in "Sonstiges".
    "categories": {
        "Entwicklung": [
            "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
            "stackexchange.com", "developer.apple.com", "developer.mozilla.org",
            "npmjs.com", "pypi.org", "docs.python.org", "readthedocs.io",
            "huggingface.co", "vercel.com", "netlify.app", "dev.to",
            "codepen.io", "hub.docker.com", "kubernetes.io", "claude.ai",
            "anthropic.com", "re:^https?://docs\\.", "re:/docs?/",
            "re:/api/reference",
        ],
        "Videos": [
            "youtube.com", "youtu.be", "vimeo.com", "twitch.tv",
            "netflix.com", "ardmediathek.de", "zdf.de", "arte.tv",
            "disneyplus.com", "primevideo.com",
        ],
        "Nachrichten": [
            "spiegel.de", "zeit.de", "faz.net", "sueddeutsche.de",
            "tagesschau.de", "heise.de", "golem.de", "t3n.de", "welt.de",
            "handelsblatt.com", "nzz.ch", "derstandard.at", "taz.de",
            "nytimes.com", "theguardian.com", "bbc.com", "bbc.co.uk",
            "reuters.com", "theverge.com", "arstechnica.com",
            "techcrunch.com", "news.ycombinator.com", "wired.com",
        ],
        "Social": [
            "reddit.com", "twitter.com", "x.com", "linkedin.com",
            "facebook.com", "instagram.com", "mastodon.social",
            "bsky.app", "threads.net", "tiktok.com",
        ],
        "Shopping": [
            "amazon.de", "amazon.com", "ebay.de", "ebay.com",
            "kleinanzeigen.de", "idealo.de", "geizhals.de", "otto.de",
            "zalando.de", "etsy.com", "mediamarkt.de", "saturn.de",
            "ikea.com", "aliexpress.com", "apple.com/de/shop", "galaxus.de",
        ],
        "Wissen & Lernen": [
            "wikipedia.org", "wikimedia.org", "medium.com", "substack.com",
            "coursera.org", "udemy.com", "khanacademy.org", "arxiv.org",
            "scholar.google.com", "researchgate.net", "duolingo.com",
        ],
        "Arbeit & Dokumente": [
            "docs.google.com", "drive.google.com", "notion.so", "notion.site",
            "figma.com", "miro.com", "trello.com", "atlassian.net",
            "airtable.com", "dropbox.com", "onedrive.live.com",
            "sharepoint.com", "canva.com",
        ],
        "Reisen & Orte": [
            "booking.com", "airbnb.de", "airbnb.com", "bahn.de",
            "maps.google.com", "maps.apple.com", "tripadvisor.de",
            "skyscanner.de", "lufthansa.com", "flixbus.de",
            "re:^https?://(www\\.)?google\\.[a-z.]+/maps",
        ],
        "Rezepte": [
            "chefkoch.de", "lecker.de", "eatsmarter.de", "kitchenstories.com",
            "allrecipes.com", "re:rezept",
        ],
        "Finanzen": [
            "paypal.com", "finanzen.net", "onvista.de", "tradingview.com",
            "comdirect.de", "ing.de", "n26.com", "trade-republic.com",
            "scalable.capital", "dkb.de",
        ],
    },
}

SEARCH_ENGINES: List[Tuple[str, str, Optional[str]]] = [
    # (Host-Regex, Pfad-Präfix, Pflicht-Query-Parameter)
    (r"(^|\.)google\.[a-z.]+$", "/search", None),
    (r"(^|\.)google\.[a-z.]+$", "/url", None),
    (r"(^|\.)bing\.com$", "/search", None),
    (r"(^|\.)duckduckgo\.com$", "/", "q"),
    (r"(^|\.)ecosia\.org$", "/search", None),
    (r"(^|\.)search\.brave\.com$", "/search", None),
    (r"(^|\.)startpage\.com$", "/", "query"),
    (r"(^|\.)search\.yahoo\.com$", "/search", None),
    (r"(^|\.)qwant\.com$", "/", "q"),
    (r"(^|\.)perplexity\.ai$", "/search", None),
    (r"(^|\.)youtube\.com$", "/results", None),
    (r"(^|\.)amazon\.[a-z.]+$", "/s", "k"),
    (r"(^|\.)ebay\.[a-z.]+$", "/sch/", None),
]

AUTH_HOSTS = [
    r"^accounts\.google\.com$", r"^login\.microsoftonline\.com$",
    r"^login\.live\.com$", r"^appleid\.apple\.com$", r"^idmsa\.apple\.com$",
    r"^auth\.", r"^login\.", r"^sso\.", r"^signin\.",
]
AUTH_PATH = re.compile(
    r"/(login|log-in|signin|sign-in|sign_in|signup|sign-up|register|logout|"
    r"log-out|signout|oauth2?|authorize|callback|auth|sso|2fa|mfa|"
    r"password[-_]?reset|verify|verification|anmelden|abmelden|"
    r"registrieren)(/|$|\?|\.)",
    re.I,
)
ERROR_TITLE = re.compile(
    r"(\b404\b|error 50\d|fehler 50\d|not found|page not found|"
    r"seite nicht gefunden|nicht gefunden|access denied|zugriff verweigert|"
    r"safari can.t open|safari kann die seite|failed to open page|"
    r"server not found|this site can.t be reached|fehler beim laden)",
    re.I,
)
EMPTY_PREFIXES = (
    "about:", "favorites://", "topsites://", "bookmarks://", "history://",
    "safari-resource:", "safari-web-extension:", "data:", "blob:",
)


# --------------------------------------------------------------------------
# Datenmodell
# --------------------------------------------------------------------------
@dataclass
class Tab:
    window: int          # Safari-Fenster-ID
    index: int           # 1-basiert innerhalb des Fensters
    title: str
    url: str
    action: str = KEEP
    reason: str = ""
    category: str = ""
    num: int = 0         # laufende Nummer in der Anzeige

    @property
    def host(self) -> str:
        return (urlsplit(self.url).hostname or "").lower()


@dataclass
class Plan:
    tabs: List[Tab] = field(default_factory=list)

    def by_action(self, action: str) -> List[Tab]:
        return [t for t in self.tabs if t.action == action]


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------
def load_config(path: Optional[str]) -> Dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if not path:
        return cfg
    with open(os.path.expanduser(path), encoding="utf-8") as fh:
        user = json.load(fh)
    for key, value in user.items():
        if key == "categories" and isinstance(value, dict):
            if user.get("replace_categories"):
                cfg["categories"] = value
            else:
                # eigene Kategorien zuerst (höhere Priorität)
                merged = dict(value)
                for k, v in cfg["categories"].items():
                    merged.setdefault(k, v)
                cfg["categories"] = merged
        else:
            cfg[key] = value
    return cfg


def _is_tracking(param: str, patterns: Iterable[str]) -> bool:
    p = param.lower()
    for pat in patterns:
        if pat.endswith("*") and p.startswith(pat[:-1].lower()):
            return True
        if p == pat.lower():
            return True
    return False


def clean_url(url: str, tracking: Iterable[str]) -> str:
    """Entfernt Tracking-Parameter, lässt die URL ansonsten unverändert."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.query:
        return url
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not _is_tracking(k, tracking)]
    return urlunsplit(parts._replace(query=urlencode(query, doseq=True)))


def normalize_url(url: str, tracking: Iterable[str] = ()) -> str:
    """Schlüssel für den Duplikat-Vergleich."""
    url = clean_url(url.strip(), tracking)
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m.") or host.startswith("mobile."):
        host = host.split(".", 1)[1]
    path = parts.path.rstrip("/") or "/"
    query = "&".join(sorted(parts.query.split("&"))) if parts.query else ""
    # YouTube: Zeitstempel ignorieren
    if host.endswith("youtube.com") and query:
        query = "&".join(q for q in query.split("&") if not q.startswith("t="))
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    return urlunsplit((scheme, host, path, query, ""))


def is_empty(tab: Tab) -> bool:
    url = tab.url.strip().lower()
    return not url or url.startswith(EMPTY_PREFIXES)


def is_search(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    params = dict(parse_qsl(parts.query))
    for host_re, path_prefix, param in SEARCH_ENGINES:
        if not re.search(host_re, host):
            continue
        if path_prefix == "/":
            ok_path = parts.path in ("", "/")
        else:
            ok_path = parts.path.startswith(path_prefix)
        if ok_path and (param is None or param in params):
            return True
    return False


def is_auth(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if any(re.search(p, host) for p in AUTH_HOSTS):
        return True
    return bool(AUTH_PATH.search(parts.path))


def categorize(tab: Tab, categories: Dict[str, List[str]]) -> str:
    host = tab.host
    if host.startswith("www."):
        host = host[4:]
    url_l = tab.url.lower()
    hostpath = host + urlsplit(tab.url).path.lower()
    for name, rules in categories.items():
        for rule in rules:
            if rule.startswith("re:"):
                if re.search(rule[3:], url_l, re.I):
                    return name
            elif "/" in rule:
                if hostpath.startswith(rule.lower()):
                    return name
            elif host == rule or host.endswith("." + rule):
                return name
    return "Sonstiges"


# --------------------------------------------------------------------------
# Analyse
# --------------------------------------------------------------------------
def analyze(tabs: List[Tab], cfg: Dict, bookmarked: Optional[set] = None) -> Plan:
    bookmarked = bookmarked or set()
    tracking = cfg["tracking_params"]
    keep_open = [re.compile(p, re.I) for p in cfg["keep_open_patterns"]]
    force_close = [re.compile(p, re.I) for p in cfg["close_patterns"]]
    force_bm = [re.compile(p, re.I) for p in cfg["bookmark_patterns"]]
    seen: Dict[str, Tab] = {}

    for n, tab in enumerate(tabs, 1):
        tab.num = n
        key = normalize_url(tab.url, tracking)

        def decide(action: str, reason: str) -> None:
            tab.action, tab.reason = action, reason

        if is_empty(tab):
            decide(CLOSE, "leerer Tab / Startseite")
        elif key in seen:
            decide(CLOSE, f"Duplikat von #{seen[key].num}")
        elif any(p.search(tab.url) for p in force_close):
            decide(CLOSE, "eigene Regel (close_patterns)")
        elif any(p.search(tab.url) for p in force_bm):
            decide(BOOKMARK, "eigene Regel (bookmark_patterns)")
        elif any(p.search(tab.url) for p in keep_open):
            decide(KEEP, "Web-App – bleibt offen")
        elif cfg["close_error_pages"] and ERROR_TITLE.search(tab.title or ""):
            decide(CLOSE, "Fehlerseite")
        elif cfg["close_search_results"] and is_search(tab.url):
            decide(CLOSE, "Suchergebnis")
        elif cfg["close_auth_pages"] and is_auth(tab.url):
            decide(CLOSE, "Login-/Anmeldeseite")
        elif cfg["close_already_bookmarked"] and key in bookmarked:
            decide(CLOSE, "schon als Lesezeichen gespeichert")
        elif tab.url.lower().startswith(("http://", "https://", "file://")):
            decide(BOOKMARK, "")
        else:
            decide(KEEP, "unbekanntes Schema")

        if key not in seen:
            seen[key] = tab
        if tab.action == BOOKMARK:
            tab.category = categorize(tab, cfg["categories"])

    return Plan(tabs)


# --------------------------------------------------------------------------
# Safari-Anbindung (osascript / JavaScript for Automation)
# --------------------------------------------------------------------------
JXA_LIST = r"""
function run() {
  const s = Application('Safari');
  const out = [];
  s.windows().forEach(w => {
    let urls, names, wid;
    try { wid = w.id(); urls = w.tabs.url(); names = w.tabs.name(); }
    catch (e) { return; }
    for (let i = 0; i < urls.length; i++) {
      out.push({window: wid, index: i + 1, title: names[i] || '', url: urls[i] || ''});
    }
  });
  return JSON.stringify(out);
}
"""

JXA_CLOSE = r"""
function run(argv) {
  const s = Application('Safari');
  const items = JSON.parse(argv[0]);   // [{window, index, url}], absteigend sortiert
  let closed = 0, skipped = 0;
  items.forEach(it => {
    try {
      const t = s.windows.byId(it.window).tabs[it.index - 1];
      if ((t.url() || '') === it.url) { t.close(); closed++; } else { skipped++; }
    } catch (e) { skipped++; }
  });
  return JSON.stringify({closed: closed, skipped: skipped});
}
"""

JXA_OPEN = r"""
function run(argv) {
  const s = Application('Safari');
  const urls = JSON.parse(argv[0]);
  if (!urls.length) return '0';
  s.activate();
  const doc = s.Document().make();
  delay(0.5);
  const w = s.windows[0];
  w.currentTab.url = urls[0];
  for (let i = 1; i < urls.length; i++) {
    w.tabs.push(s.Tab({url: urls[i]}));
  }
  return String(urls.length);
}
"""


def require_macos() -> None:
    if sys.platform != "darwin":
        sys.exit("Dieses Kommando braucht macOS mit Safari. "
                 "(Zum Testen: --from-json tabs.json)")


def osascript(script: str, *args: str) -> str:
    proc = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script, *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip()
        if "-1743" in err or "not allowed" in err.lower():
            sys.exit(
                "Kein Zugriff auf Safari. Bitte erlauben unter\n"
                "  Systemeinstellungen → Datenschutz & Sicherheit → "
                "Automation → Terminal → Safari"
            )
        sys.exit(f"osascript-Fehler: {err}")
    return proc.stdout.strip()


def safari_running() -> bool:
    return subprocess.run(["pgrep", "-xq", "Safari"]).returncode == 0


def read_safari_tabs() -> List[Tab]:
    require_macos()
    if not safari_running():
        sys.exit("Safari läuft nicht.")
    data = json.loads(osascript(JXA_LIST) or "[]")
    return [Tab(window=d["window"], index=d["index"], title=d["title"],
                url=d["url"]) for d in data]


def close_tabs(tabs: List[Tab]) -> Dict:
    # pro Fenster von hinten nach vorne schließen, damit Indizes stimmen
    items = sorted(
        ({"window": t.window, "index": t.index, "url": t.url} for t in tabs),
        key=lambda d: (d["window"], -d["index"]),
    )
    if not items:
        return {"closed": 0, "skipped": 0}
    return json.loads(osascript(JXA_CLOSE, json.dumps(items)))


# --------------------------------------------------------------------------
# Lesezeichen lesen / schreiben
# --------------------------------------------------------------------------
def iter_bookmark_urls(node: Dict) -> Iterable[str]:
    if node.get("WebBookmarkType") == "WebBookmarkTypeLeaf":
        url = node.get("URLString")
        if url:
            yield url
    for child in node.get("Children", []) or []:
        yield from iter_bookmark_urls(child)


def load_bookmarks(path: Path = BOOKMARKS_PLIST) -> Optional[Dict]:
    try:
        with open(path, "rb") as fh:
            return plistlib.load(fh)
    except FileNotFoundError:
        return None
    except PermissionError:
        print("⚠️  Kein Lesezugriff auf Safari-Lesezeichen (Bookmarks.plist).\n"
              "   Für die Erkennung bereits gespeicherter Seiten und --direct:\n"
              "   Systemeinstellungen → Datenschutz & Sicherheit → "
              "Festplattenvollzugriff → Terminal aktivieren.\n", file=sys.stderr)
        return None


def _new_folder(title: str) -> Dict:
    return {
        "WebBookmarkType": "WebBookmarkTypeList",
        "Title": title,
        "WebBookmarkUUID": str(uuid.uuid4()).upper(),
        "Children": [],
    }


def _new_leaf(title: str, url: str) -> Dict:
    return {
        "WebBookmarkType": "WebBookmarkTypeLeaf",
        "URLString": url,
        "URIDictionary": {"title": title or url},
        "WebBookmarkUUID": str(uuid.uuid4()).upper(),
    }


def group_for_bookmarks(tabs: List[Tab], cfg: Dict) -> Dict[str, List[Tab]]:
    order = list(cfg["categories"].keys()) + ["Sonstiges"]
    groups: Dict[str, List[Tab]] = {}
    for t in tabs:
        groups.setdefault(t.category or "Sonstiges", []).append(t)
    for items in groups.values():
        items.sort(key=lambda t: (re.sub(r"^www\.", "", t.host), (t.title or "").lower()))
    return {k: groups[k] for k in sorted(groups, key=lambda c: order.index(c)
                                         if c in order else len(order))}


def add_to_bookmark_tree(root: Dict, tabs: List[Tab], cfg: Dict) -> int:
    """Fügt Tabs unter <folder>/<Kategorie> ein. Gibt Anzahl neuer Einträge zurück."""
    tracking = cfg["tracking_params"]
    existing = {normalize_url(u, tracking) for u in iter_bookmark_urls(root)}
    children = root.setdefault("Children", [])
    top = next((c for c in children if c.get("WebBookmarkType") == "WebBookmarkTypeList"
                and c.get("Title") == cfg["folder"]), None)
    if top is None:
        top = _new_folder(cfg["folder"])
        # hinter Favoriten/Lesezeichenmenü einsortieren
        pos = sum(1 for c in children if c.get("Title") in
                  ("BookmarksBar", "BookmarksMenu"))
        children.insert(pos, top)
    added = 0
    for cat, items in group_for_bookmarks(tabs, cfg).items():
        sub = next((c for c in top["Children"] if c.get("Title") == cat
                    and c.get("WebBookmarkType") == "WebBookmarkTypeList"), None)
        if sub is None:
            sub = _new_folder(cat)
            top["Children"].append(sub)
        for t in items:
            url = clean_url(t.url, tracking)
            key = normalize_url(url, tracking)
            if key in existing:
                continue
            existing.add(key)
            sub["Children"].append(_new_leaf(t.title, url))
            added += 1
    return added


def write_bookmarks_plist(tabs: List[Tab], cfg: Dict,
                          path: Path = BOOKMARKS_PLIST) -> Tuple[int, Path]:
    with open(path, "rb") as fh:
        root = plistlib.load(fh)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"Bookmarks.plist.backup-{stamp}")
    shutil.copy2(path, backup)
    added = add_to_bookmark_tree(root, tabs, cfg)
    tmp = path.with_suffix(".plist.tmp")
    with open(tmp, "wb") as fh:
        plistlib.dump(root, fh, fmt=plistlib.FMT_BINARY)
    os.replace(tmp, path)
    return added, backup


def export_html(tabs: List[Tab], cfg: Dict, out: Path) -> int:
    """Netscape-Bookmark-Datei (Safari: Ablage → Importieren von → Lesezeichen-HTML-Datei)."""
    tracking = cfg["tracking_params"]
    now = int(time.time())
    date = _dt.date.today().isoformat()
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>",
        f'    <DT><H3 ADD_DATE="{now}">{html.escape(cfg["folder"])} {date}</H3>',
        "    <DL><p>",
    ]
    count = 0
    for cat, items in group_for_bookmarks(tabs, cfg).items():
        lines.append(f'        <DT><H3 ADD_DATE="{now}">{html.escape(cat)}</H3>')
        lines.append("        <DL><p>")
        for t in items:
            url = clean_url(t.url, tracking)
            lines.append(f'            <DT><A HREF="{html.escape(url, quote=True)}" '
                         f'ADD_DATE="{now}">{html.escape(t.title or url)}</A>')
            count += 1
        lines.append("        </DL><p>")
    lines += ["    </DL><p>", "</DL><p>", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return count


# --------------------------------------------------------------------------
# Ausgabe & Interaktion
# --------------------------------------------------------------------------
def _short(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def print_plan(plan: Plan) -> None:
    width = shutil.get_terminal_size((110, 20)).columns
    tw = max(20, min(50, width - 60))
    icons = {CLOSE: "✖", BOOKMARK: "★", KEEP: "•"}
    for t in plan.tabs:
        info = t.category if t.action == BOOKMARK else t.reason
        print(f"{t.num:>3} {icons[t.action]} {ACTION_LABEL[t.action]:<11} "
              f"{_short(t.title or t.url, tw):<{tw}}  {_short(t.host, 24):<24} "
              f"{_short(info, 30)}")
    print()
    print_summary(plan)


def print_summary(plan: Plan) -> None:
    c, b, k = (len(plan.by_action(a)) for a in (CLOSE, BOOKMARK, KEEP))
    print(f"{len(plan.tabs)} Tabs: {c} schließen · {b} als Lesezeichen · {k} behalten")
    cats: Dict[str, int] = {}
    for t in plan.by_action(BOOKMARK):
        cats[t.category] = cats.get(t.category, 0) + 1
    if cats:
        print("Kategorien: " + ", ".join(f"{k} ({v})" for k, v in
                                         sorted(cats.items(), key=lambda x: -x[1])))


def interactive_review(plan: Plan, cfg: Dict) -> bool:
    help_text = (
        "Aktion ändern: Nummern + Buchstabe, z. B. '3s 7l 12b' "
        "(s = schließen, l = Lesezeichen, b = behalten),\n"
        "'5-9s' für Bereiche, 'k 4 Videos' setzt Kategorie, "
        "Enter = ausführen, q = abbrechen."
    )
    by_num = {t.num: t for t in plan.tabs}
    while True:
        print(help_text)
        try:
            ans = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if not ans:
            return True
        if ans.lower() in ("q", "quit", "exit", "abbrechen"):
            return False
        m = re.match(r"^k\s+(\d+)\s+(.+)$", ans, re.I)
        if m:
            t = by_num.get(int(m.group(1)))
            if t:
                t.action, t.category = BOOKMARK, m.group(2).strip()
        else:
            for tok in ans.replace(",", " ").split():
                mm = re.match(r"^(\d+)(?:-(\d+))?([slb])$", tok, re.I)
                if not mm:
                    print(f"  ? '{tok}' nicht verstanden")
                    continue
                a, b = int(mm.group(1)), int(mm.group(2) or mm.group(1))
                for n in range(a, b + 1):
                    t = by_num.get(n)
                    if not t:
                        continue
                    t.action = ACTION_KEY[mm.group(3).lower()]
                    t.reason = "manuell"
                    if t.action == BOOKMARK and not t.category:
                        t.category = categorize(t, cfg["categories"])
        print()
        print_plan(plan)


def write_report(plan: Plan, out: Path) -> None:
    lines = [f"# Safari-Tab-Bericht {_dt.datetime.now():%Y-%m-%d %H:%M}", ""]
    for action, head in ((BOOKMARK, "Als Lesezeichen gesichert"),
                         (CLOSE, "Geschlossen"), (KEEP, "Offen gelassen")):
        items = plan.by_action(action)
        if not items:
            continue
        lines += [f"## {head} ({len(items)})", ""]
        for t in items:
            extra = t.category if action == BOOKMARK else t.reason
            title = (t.title or t.url).replace("[", "(").replace("]", ")")
            lines.append(f"- [{title}]({t.url})" + (f" — {extra}" if extra else ""))
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Direktes Schreiben in Safari (Safari kurz beenden)
# --------------------------------------------------------------------------
def direct_write(tabs_to_save: List[Tab], cfg: Dict) -> None:
    remaining = [t.url for t in read_safari_tabs() if not is_empty(t)]
    print("Safari wird kurz beendet, um die Lesezeichen einzutragen …")
    osascript("function run(){ Application('Safari').quit(); }")
    for _ in range(40):
        if not safari_running():
            break
        time.sleep(0.25)
    else:
        sys.exit("Safari hat sich nicht beendet – Lesezeichen nicht geschrieben.")
    time.sleep(0.5)
    try:
        added, backup = write_bookmarks_plist(tabs_to_save, cfg)
        print(f"★ {added} Lesezeichen in „{cfg['folder']}“ eingetragen "
              f"(Sicherung: {backup.name})")
    except PermissionError:
        print("⚠️  Kein Schreibzugriff auf Bookmarks.plist – Terminal braucht "
              "Festplattenvollzugriff. Exportiere stattdessen HTML.", file=sys.stderr)
        out = default_export_path()
        export_html(tabs_to_save, cfg, out)
        print(f"   HTML-Datei: {out}")
    finally:
        subprocess.run(["open", "-a", "Safari"])
        time.sleep(3)
        restore_missing(remaining)


def restore_missing(urls: List[str]) -> None:
    """Öffnet Tabs wieder, falls Safari das letzte Fenster nicht wiederhergestellt hat."""
    if not urls:
        return
    try:
        now = {normalize_url(t.url) for t in read_safari_tabs()}
    except SystemExit:
        now = set()
    missing = [u for u in urls if normalize_url(u) not in now]
    if len(missing) > len(urls) / 2:
        osascript(JXA_OPEN, json.dumps(missing))
        print(f"↺ {len(missing)} Tabs wieder geöffnet.")


def default_export_path() -> Path:
    base = Path.home() / "Downloads"
    if not base.is_dir():
        base = Path.cwd()
    return base / f"safari-lesezeichen-{_dt.datetime.now():%Y%m%d-%H%M}.html"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="safari-tabs",
        description="Analysiert Safari-Tabs, schließt unnötige und sichert "
                    "die wichtigen geordnet als Lesezeichen.",
    )
    ap.add_argument("-n", "--dry-run", action="store_true",
                    help="nur analysieren, nichts schließen oder speichern")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="ohne Rückfrage ausführen")
    ap.add_argument("--close-saved", action="store_true",
                    help="als Lesezeichen gesicherte Tabs danach auch schließen")
    ap.add_argument("--direct", action="store_true",
                    help="Lesezeichen direkt in Safari eintragen (Safari wird "
                         "dafür kurz beendet, braucht Festplattenvollzugriff)")
    ap.add_argument("--export", metavar="DATEI",
                    help="Pfad für die Lesezeichen-HTML-Datei "
                         "(Standard: ~/Downloads/safari-lesezeichen-….html)")
    ap.add_argument("--report", metavar="DATEI", help="Markdown-Bericht schreiben")
    ap.add_argument("--folder", help="Name des Lesezeichen-Ordners (Standard: Tab-Archiv)")
    ap.add_argument("--config", metavar="DATEI", help="eigene Regeln (JSON)")
    ap.add_argument("--dump-config", action="store_true",
                    help="Standard-Konfiguration ausgeben und beenden")
    ap.add_argument("--from-json", metavar="DATEI",
                    help="Tabs aus JSON-Datei statt aus Safari lesen (Test)")
    ap.add_argument("--json", action="store_true",
                    help="Analyse als JSON ausgeben und beenden")
    args = ap.parse_args(argv)

    if args.dump_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
        return 0

    cfg = load_config(args.config)
    if args.folder:
        cfg["folder"] = args.folder

    offline = bool(args.from_json)
    if offline:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        tabs = [Tab(window=d.get("window", 1), index=d.get("index", i + 1),
                    title=d.get("title", ""), url=d.get("url", ""))
                for i, d in enumerate(data)]
    else:
        tabs = read_safari_tabs()
    if not tabs:
        print("Keine Tabs gefunden.")
        return 0

    root = None if offline else load_bookmarks()
    bookmarked = ({normalize_url(u, cfg["tracking_params"]) for u in iter_bookmark_urls(root)}
                  if root else set())
    plan = analyze(tabs, cfg, bookmarked)

    if args.json:
        print(json.dumps([t.__dict__ for t in plan.tabs], indent=2, ensure_ascii=False))
        return 0

    print_plan(plan)
    if args.report:
        write_report(plan, Path(args.report).expanduser())
        print(f"Bericht: {args.report}")
    if args.dry_run:
        return 0
    if not args.yes and not interactive_review(plan, cfg):
        print("Abgebrochen – nichts geändert.")
        return 1

    to_save = plan.by_action(BOOKMARK)
    to_close = plan.by_action(CLOSE) + (to_save if args.close_saved else [])

    # 1) Lesezeichen zuerst sichern (HTML immer als Backup)
    if to_save:
        out = Path(args.export).expanduser() if args.export else default_export_path()
        n = export_html(to_save, cfg, out)
        print(f"★ {n} Lesezeichen exportiert: {out}")

    # 2) Tabs schließen
    if offline:
        print(f"(offline) würde {len(to_close)} Tabs schließen.")
    elif to_close:
        res = close_tabs(to_close)
        print(f"✖ {res['closed']} Tabs geschlossen"
              + (f", {res['skipped']} übersprungen (inzwischen verändert)"
                 if res["skipped"] else ""))

    # 3) Lesezeichen in Safari übernehmen
    if to_save and not offline:
        if args.direct:
            direct_write(to_save, cfg)
        else:
            print("\nZum Übernehmen in Safari: Ablage → Importieren von → "
                  "Lesezeichen-HTML-Datei … → die Datei oben wählen.\n"
                  "(Oder nächstes Mal mit --direct automatisch eintragen.)")
            subprocess.run(["open", "-R", str(out)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
