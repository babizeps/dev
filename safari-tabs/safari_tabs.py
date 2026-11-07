#!/usr/bin/env python3
"""safari-tabs – räumt Safari-Tabs auf.

1. Überblick: zeigt alle offenen Safari-Tabs und empfiehlt, welche geschlossen
   werden können (Duplikate, leere Tabs, Suchergebnisse, Login-/Fehlerseiten,
   bereits gespeicherte Seiten …).
2. Schließt die empfohlenen Tabs (nach Bestätigung).
3. Sortiert die übrigen Tabs in deine *vorhandenen* Lesezeichen-Ordner ein –
   passend nach Domain, Stichworten im Ordnernamen und Thema.

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
import sqlite3
import tempfile
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BOOKMARKS_PLIST = Path.home() / "Library" / "Safari" / "Bookmarks.plist"
# iCloud-Tabs anderer Geräte (iPhone, iPad, andere Macs), von Safari synchronisiert
CLOUD_TABS_DBS = [
    Path.home() / "Library" / "Containers" / "com.apple.Safari" / "Data" / "Library"
    / "Safari" / "CloudTabs.db",
    Path.home() / "Library" / "Safari" / "CloudTabs.db",
]

CLOSE = "close"
BOOKMARK = "bookmark"
KEEP = "keep"

ACTION_LABEL = {CLOSE: "schließen", BOOKMARK: "Lesezeichen", KEEP: "behalten"}
ACTION_KEY = {"s": CLOSE, "l": BOOKMARK, "b": KEEP}

# --------------------------------------------------------------------------
# Standard-Konfiguration (kann per --config JSON-Datei überschrieben werden)
# --------------------------------------------------------------------------
DEFAULT_CONFIG: Dict = {
    # Ordner für Tabs, die zu keinem vorhandenen Ordner passen
    # (wird nur angelegt, wenn nötig)
    "fallback_folder": "Unsortiert",
    # Mindestpunktzahl, damit ein Tab einem vorhandenen Ordner zugeordnet wird
    "min_match_score": 3,
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

# Ordnernamen-Stichworte, die zu einem Thema passen (für die Zuordnung zu
# vorhandenen Lesezeichen-Ordnern)
CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "Entwicklung": ["dev", "development", "entwicklung", "programmieren",
                    "programming", "code", "coding", "software", "tech",
                    "technik", "python", "javascript", "web", "informatik",
                    "github", "docs", "doku", "dokumentation"],
    "Videos": ["video", "videos", "youtube", "film", "filme", "serien",
               "streaming", "anschauen", "watch", "musik", "music", "mediathek"],
    "Nachrichten": ["news", "nachrichten", "artikel", "presse", "zeitung",
                    "lesen", "read", "später", "later", "aktuell"],
    "Social": ["social", "soziale", "netzwerke", "community", "reddit"],
    "Shopping": ["shopping", "einkaufen", "kaufen", "wunschliste", "wishlist",
                 "shop", "produkte", "geschenke", "geschenkideen"],
    "Wissen & Lernen": ["wissen", "lernen", "learning", "bildung", "studium",
                        "uni", "schule", "wiki", "recherche", "research",
                        "kurse", "sprachen"],
    "Arbeit & Dokumente": ["arbeit", "work", "job", "büro", "buero", "projekte",
                           "projekt", "dokumente", "tools", "firma", "office"],
    "Reisen & Orte": ["reisen", "reise", "travel", "urlaub", "orte", "karten",
                      "ausflug", "ausflüge", "hotels"],
    "Rezepte": ["rezepte", "rezept", "kochen", "essen", "food", "backen",
                "recipes", "küche", "kueche"],
    "Finanzen": ["finanzen", "finance", "geld", "banking", "bank", "aktien",
                 "investieren", "steuern", "versicherung"],
}

# Art des Inhalts (Video, Artikel, Tool …). Passt sehr gut zu Ordnern, die nach
# Inhaltsart benannt sind. Reihenfolge = Priorität.
#   "label":  Anzeige
#   "folder_words": Wörter im Ordnernamen, die zu dieser Art passen
#   "rules":  Domain, domain/pfad oder "re:" + Regex (auf URL), "title:" + Regex (auf Titel)
KINDS: Dict[str, Dict] = {
    "ai-chat": {
        "label": "KI-Chat",
        "folder_words": ["ai", "ki", "chat", "chats", "gpt", "llm", "prompts", "prompt",
                         "chatbot", "chatbots", "assistant"],
        "rules": ["chatgpt.com", "chat.openai.com", "claude.ai", "gemini.google.com",
                  "aistudio.google.com", "perplexity.ai", "copilot.microsoft.com",
                  "poe.com", "chat.mistral.ai", "chat.deepseek.com", "grok.com",
                  "x.com/i/grok", "huggingface.co/chat", "meta.ai", "you.com",
                  "notebooklm.google.com", "chat.qwen.ai", "le-chat.mistral.ai"],
    },
    "video": {
        "label": "Video",
        "folder_words": ["video", "videos", "youtube", "film", "filme", "movies",
                         "watch", "anschauen", "mediathek", "clips", "serien"],
        "rules": ["youtube.com", "youtu.be", "vimeo.com", "twitch.tv", "netflix.com",
                  "dailymotion.com", "ted.com", "ardmediathek.de", "zdf.de",
                  "arte.tv", "3sat.de", "primevideo.com", "disneyplus.com",
                  "joyn.de", "loom.com", "tiktok.com", "nebula.tv",
                  "re:/videos?/", "title:\\b(video|trailer|livestream)\\b"],
    },
    "event": {
        "label": "Event",
        "folder_words": ["event", "events", "veranstaltung", "veranstaltungen",
                         "termine", "tickets", "konzerte", "konferenz", "konferenzen",
                         "meetups", "festival", "festivals"],
        "rules": ["eventbrite.com", "eventbrite.de", "meetup.com", "lu.ma", "luma.com",
                  "eventim.de", "ticketmaster.de", "ticketmaster.com", "reservix.de",
                  "rausgegangen.de", "dice.fm", "residentadvisor.net", "ra.co",
                  "facebook.com/events", "sessionize.com", "pretix.eu", "tito.io",
                  "re:/(events?|veranstaltungen?|tickets?)/",
                  "title:\\b(tickets?|konferenz|conference|festival|webinar|meetup|"
                  "workshop|konzert|veranstaltung|summit)\\b"],
    },
    "forum": {
        "label": "Forum",
        "folder_words": ["forum", "foren", "forums", "community", "communities",
                         "diskussion", "diskussionen", "discussion", "threads", "reddit"],
        "rules": ["reddit.com", "stackoverflow.com", "stackexchange.com",
                  "superuser.com", "serverfault.com", "askubuntu.com",
                  "news.ycombinator.com", "lobste.rs", "quora.com", "gutefrage.net",
                  "discussions.apple.com", "forums.macrumors.com", "discord.com",
                  "community.", "re:^https?://(forum|forums|community|discuss|discourse)\\.",
                  "re:/(forum|forums|community|discussions?|threads?)/",
                  "re:/t/[^/]+/\\d+", "github.com/[^/]+/[^/]+/(issues|discussions)"],
    },
    "book": {
        "label": "Buch",
        "folder_words": ["book", "books", "buch", "bücher", "buecher", "lesen",
                         "reading", "bibliothek", "hörbücher", "audiobooks", "ebooks"],
        "rules": ["goodreads.com", "thalia.de", "hugendubel.de", "buecher.de",
                  "books.google.com", "audible.de", "audible.com", "openlibrary.org",
                  "gutenberg.org", "projekt-gutenberg.org", "perlentaucher.de",
                  "storygraph.com", "oreilly.com/library", "manning.com", "leanpub.com",
                  "re:isbn", "re:/(buch|book|books|ebook)/",
                  "title:\\b(buch|roman|hörbuch|ebook|e-book|taschenbuch|"
                  "gebundene ausgabe|hardcover|paperback|kindle edition)\\b"],
    },
    "shop": {
        "label": "Shop",
        "folder_words": ["shop", "shops", "shopping", "einkaufen", "kaufen",
                         "wunschliste", "wishlist", "store", "produkte", "geschenke"],
        "rules": ["amazon.de", "amazon.com", "ebay.de", "ebay.com", "kleinanzeigen.de",
                  "idealo.de", "geizhals.de", "otto.de", "zalando.de", "etsy.com",
                  "mediamarkt.de", "saturn.de", "ikea.com", "aliexpress.com", "temu.com",
                  "galaxus.de", "about-you.de", "aboutyou.de", "decathlon.de",
                  "apple.com/de/shop", "apple.com/shop", "re:/(products?|produkt|dp|item|artikel/\\d)/",
                  "re:(warenkorb|/cart|/checkout)", "re:^https?://shop\\.",
                  "re:^https?://[^/]*store\\."],
    },
    "tool": {
        "label": "Tool",
        "folder_words": ["tool", "tools", "werkzeug", "werkzeuge", "apps", "app",
                         "software", "utilities", "utils", "dienste", "services", "helfer"],
        "rules": ["github.com", "gitlab.com", "figma.com", "canva.com", "notion.so",
                  "miro.com", "trello.com", "airtable.com", "deepl.com", "translate.google.com",
                  "regex101.com", "smallpdf.com", "ilovepdf.com", "tinypng.com",
                  "remove.bg", "excalidraw.com", "draw.io", "app.diagrams.net",
                  "photopea.com", "squoosh.app", "codepen.io", "jsfiddle.net",
                  "replit.com", "vercel.com", "netlify.com", "zapier.com", "make.com",
                  "producthunt.com", "alternativeto.net", "apps.apple.com",
                  "chromewebstore.google.com", "addons.mozilla.org", "huggingface.co",
                  "docs.google.com", "sheets.google.com", "drive.google.com",
                  "re:^https?://app\\.",
                  "title:\\b(tool|generator|converter|konverter|rechner|calculator|"
                  "editor|online[- ]tool|app)\\b"],
    },
    "article": {
        "label": "Artikel",
        "folder_words": ["article", "articles", "artikel", "read", "lesen", "später",
                         "later", "news", "nachrichten", "blog", "blogs", "posts",
                         "beiträge", "essays", "readlater", "lesestoff"],
        "rules": ["medium.com", "substack.com", "wikipedia.org", "spiegel.de", "zeit.de",
                  "faz.net", "sueddeutsche.de", "tagesschau.de", "heise.de", "golem.de",
                  "t3n.de", "welt.de", "handelsblatt.com", "nzz.ch", "derstandard.at",
                  "taz.de", "nytimes.com", "theguardian.com", "bbc.com", "bbc.co.uk",
                  "reuters.com", "theverge.com", "arstechnica.com", "techcrunch.com",
                  "wired.com", "economist.com", "theatlantic.com", "dev.to",
                  "hashnode.dev", "ghost.io", "wordpress.com", "blogspot.com",
                  "re:/(article|articles|artikel|blog|news|posts?|story|stories|"
                  "magazin|magazine)/", "re:/20\\d\\d/\\d\\d/"],
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
    kind: str = ""           # Inhaltsart (Schlüssel aus KINDS)
    num: int = 0         # laufende Nummer in der Anzeige
    # Ziel-Lesezeichenordner
    target_key: str = ""     # UUID oder Pfad des Ordners
    target_path: str = ""    # Anzeige, z. B. "Favoriten/Dev"
    target_new: bool = False  # Ordner existiert noch nicht
    target_why: str = ""
    device: str = ""         # leer = dieser Mac, sonst z. B. "iPhone von Jürgen"

    @property
    def remote(self) -> bool:
        return bool(self.device)

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


def _rule_matches(rule: str, tab: Tab, host: str, hostpath: str) -> bool:
    if rule.startswith("re:"):
        return re.search(rule[3:], tab.url, re.I) is not None
    if rule.startswith("title:"):
        return re.search(rule[6:], tab.title or "", re.I) is not None
    if rule.endswith(".") and "/" not in rule:          # z. B. "community."
        return host.startswith(rule)
    if "/" in rule:
        if any(ch in rule for ch in "[]()^$+*?\\"):
            return re.match(rule, hostpath, re.I) is not None
        return hostpath.startswith(rule.lower())
    return host == rule or host.endswith("." + rule)


def detect_kind(tab: Tab) -> Tuple[str, bool]:
    """Liefert (Inhaltsart, sicher?). Unsicher = nur aus der URL-Form geraten."""
    host = (tab.host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    hostpath = host + urlsplit(tab.url).path.lower()
    for kind, spec in KINDS.items():
        if any(_rule_matches(r, tab, host, hostpath) for r in spec["rules"]):
            return kind, True
    # Heuristik: tiefer Pfad / sprechender Slug → vermutlich Artikel
    path = urlsplit(tab.url).path.strip("/")
    last = path.rsplit("/", 1)[-1]
    if path and (path.count("/") >= 2 or last.count("-") >= 2):
        return "article", False
    return "", False


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
def analyze(tabs: List[Tab], cfg: Dict,
            bookmarked: Optional[Dict[str, str]] = None) -> Plan:
    """bookmarked: normalisierte URL → Ordnerpfad, in dem sie schon liegt."""
    bookmarked = bookmarked or {}
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
            other = seen[key]
            if other.device != tab.device:
                decide(CLOSE, f"auch {'auf ' + other.device if other.device else 'am Mac'} "
                              f"offen (#{other.num})")
            else:
                decide(CLOSE, f"Duplikat von #{other.num}")
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
            where = bookmarked[key]
            decide(CLOSE, f"schon gespeichert in {where}" if where
                   else "schon als Lesezeichen gespeichert")
        elif tab.url.lower().startswith(("http://", "https://", "file://")):
            decide(BOOKMARK, "")
        else:
            decide(KEEP, "unbekanntes Schema")

        if key not in seen:
            seen[key] = tab
        if tab.action == BOOKMARK:
            tab.category = categorize(tab, cfg["categories"])
            tab.kind, sure = detect_kind(tab)
            if tab.kind and not sure:
                tab.kind = "~" + tab.kind

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


def local_computer_name() -> str:
    try:
        out = subprocess.run(["scutil", "--get", "ComputerName"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _cf_time(value) -> Optional[_dt.datetime]:
    """Apple-Zeitstempel (Sekunden seit 2001) → datetime, falls plausibel."""
    try:
        ts = float(value) + 978307200
        d = _dt.datetime.fromtimestamp(ts)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return d if 2015 <= d.year <= _dt.date.today().year + 1 else None


def read_cloud_tabs(db_path: Optional[Path] = None,
                    exclude_devices: Iterable[str] = ()) -> Tuple[List[Tab], List[Dict]]:
    """Liest die per iCloud synchronisierten Tabs anderer Geräte.

    Gibt (Tabs, Geräteliste) zurück. Die Datenbank wird in einen temporären
    Ordner kopiert, damit Safari nicht gestört wird. Fehlt die Datei oder der
    Zugriff, wird PermissionError/FileNotFoundError ausgelöst.
    """
    candidates = [db_path] if db_path else CLOUD_TABS_DBS
    src = next((p for p in candidates if p and p.exists()), None)
    if src is None:
        raise FileNotFoundError("CloudTabs.db nicht gefunden – ist Safari in den "
                                "iCloud-Einstellungen eingeschaltet?")
    exclude = {e.strip().lower() for e in exclude_devices if e}
    with tempfile.TemporaryDirectory() as tmp:
        for suffix in ("", "-wal", "-shm"):
            f = Path(str(src) + suffix)
            if f.exists():
                shutil.copy2(f, Path(tmp) / (src.name + suffix))  # PermissionError ohne FDA
        con = sqlite3.connect(str(Path(tmp) / src.name))
        try:
            con.row_factory = sqlite3.Row
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "cloud_tabs" not in tables:
                raise FileNotFoundError("Unbekanntes Format von CloudTabs.db")

            def cols(table: str) -> set:
                return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}

            devices: Dict[str, Dict] = {}
            if "cloud_tab_devices" in tables:
                dc = cols("cloud_tab_devices")
                sel = ["device_uuid", "device_name"] + \
                      (["last_modified"] if "last_modified" in dc else [])
                for r in con.execute(f"SELECT {', '.join(sel)} FROM cloud_tab_devices"):
                    last = _cf_time(r["last_modified"]) if "last_modified" in sel else None
                    devices[r["device_uuid"]] = {
                        "name": r["device_name"] or "Anderes Gerät",
                        "zuletzt": last.strftime("%d.%m.%Y %H:%M") if last else None,
                        "tabs": 0,
                    }
            tc = cols("cloud_tabs")
            order = " ORDER BY device_uuid, position" if "position" in tc else ""
            sel = ["device_uuid", "title", "url"] + (["is_pinned"] if "is_pinned" in tc else [])
            tabs: List[Tab] = []
            for r in con.execute(f"SELECT {', '.join(sel)} FROM cloud_tabs{order}"):
                dev = devices.setdefault(r["device_uuid"], {
                    "name": "Anderes Gerät", "zuletzt": None, "tabs": 0})
                if dev["name"].strip().lower() in exclude:
                    continue
                dev["tabs"] += 1
                tabs.append(Tab(window=0, index=0, title=r["title"] or "",
                                url=r["url"] or "", device=dev["name"]))
        finally:
            con.close()
    dev_list = [{"geraet": d["name"], "tabs": d["tabs"], "zuletzt_synchronisiert": d["zuletzt"]}
                for d in devices.values()
                if d["name"].strip().lower() not in exclude and d["tabs"]]
    return tabs, dev_list


def read_all_tabs(include_cloud: bool = True) -> Tuple[List[Tab], List[Dict], Optional[str]]:
    """Mac-Tabs + (optional) iCloud-Tabs. Gibt (Tabs, Geräte, Hinweis) zurück."""
    tabs = read_safari_tabs()
    if not include_cloud:
        return tabs, [], None
    try:
        remote, devices = read_cloud_tabs(exclude_devices=[local_computer_name()])
    except PermissionError:
        return tabs, [], ("iPhone-/iPad-Tabs nicht lesbar: Festplattenvollzugriff fehlt "
                          "(Systemeinstellungen → Datenschutz & Sicherheit → "
                          "Festplattenvollzugriff).")
    except (FileNotFoundError, sqlite3.Error) as e:
        return tabs, [], f"iPhone-/iPad-Tabs nicht verfügbar: {e}"
    return tabs + remote, devices, None


def split_local_remote(tabs: List[Tab]) -> Tuple[List[Tab], List[Tab]]:
    return [t for t in tabs if not t.remote], [t for t in tabs if t.remote]


# --------------------------------------------------------------------------
# Vorhandene Lesezeichen-Ordner
# --------------------------------------------------------------------------
SPECIAL_TITLES = {"BookmarksBar": "Favoriten", "BookmarksMenu": "Lesezeichenmenü"}
SKIP_TITLES = {"com.apple.ReadingList"}
STOPWORDS = {"und", "the", "and", "für", "fuer", "von", "der", "die", "das",
             "mit", "neu", "new", "alt", "old", "misc", "sonstiges", "diverses",
             "allgemein", "www", "com", "http", "https", "html", "php"}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-zäöüß0-9]+", (text or "").lower())
            if len(w) >= 2 and w not in STOPWORDS}


def _bare_host(host: str) -> str:
    host = (host or "").lower()
    for pre in ("www.", "m.", "mobile."):
        if host.startswith(pre):
            return host[len(pre):]
    return host


def _domain(host: str) -> str:
    """Grobe registrierbare Domain: news.bbc.co.uk → bbc.co.uk"""
    parts = _bare_host(host).split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in (
            "co", "com", "org", "net", "gov", "ac", "or", "ne"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


@dataclass
class Folder:
    key: str               # WebBookmarkUUID (oder Pfad, falls keine UUID)
    path: str              # "Favoriten/Dev/Python"
    title: str
    depth: int
    hosts: Dict[str, int] = field(default_factory=dict)    # direkte Lesezeichen
    domains: Dict[str, int] = field(default_factory=dict)
    sub_domains: Dict[str, int] = field(default_factory=dict)  # in Unterordnern
    leaves: int = 0
    tokens: set = field(default_factory=set)
    num: int = 0


def _node_title(node: Dict) -> str:
    t = node.get("Title", "")
    return SPECIAL_TITLES.get(t, t)


def collect_folders(root: Dict) -> List[Folder]:
    folders: List[Folder] = []

    def walk(node: Dict, prefix: str, depth: int) -> Dict[str, int]:
        title = _node_title(node)
        path = f"{prefix}/{title}" if prefix else title
        f = Folder(key=node.get("WebBookmarkUUID") or path, path=path,
                   title=title, depth=depth, tokens=_tokens(title))
        folders.append(f)
        below: Dict[str, int] = {}
        for c in node.get("Children", []) or []:
            typ = c.get("WebBookmarkType")
            if typ == "WebBookmarkTypeLeaf":
                h = _bare_host(urlsplit(c.get("URLString", "")).hostname or "")
                if h:
                    f.hosts[h] = f.hosts.get(h, 0) + 1
                    d = _domain(h)
                    f.domains[d] = f.domains.get(d, 0) + 1
                    f.leaves += 1
            elif typ == "WebBookmarkTypeList" and c.get("Title") not in SKIP_TITLES:
                for d, n in walk(c, path, depth + 1).items():
                    below[d] = below.get(d, 0) + n
        f.sub_domains = below
        total = dict(below)
        for d, n in f.domains.items():
            total[d] = total.get(d, 0) + n
        return total

    for c in root.get("Children", []) or []:
        if c.get("WebBookmarkType") == "WebBookmarkTypeList" \
                and c.get("Title") not in SKIP_TITLES:
            walk(c, "", 0)
    for i, f in enumerate(folders, 1):
        f.num = i
    return folders


def bookmark_index(root: Optional[Dict], tracking: Iterable[str]) -> Dict[str, str]:
    """normalisierte URL → Ordnerpfad"""
    out: Dict[str, str] = {}
    if not root:
        return out

    def walk(node: Dict, path: str) -> None:
        for c in node.get("Children", []) or []:
            typ = c.get("WebBookmarkType")
            if typ == "WebBookmarkTypeLeaf" and c.get("URLString"):
                out.setdefault(normalize_url(c["URLString"], tracking), path)
            elif typ == "WebBookmarkTypeList" and c.get("Title") not in SKIP_TITLES:
                t = _node_title(c)
                walk(c, f"{path}/{t}" if path else t)

    walk(root, "")
    return out


def iter_bookmark_urls(node: Dict) -> Iterable[str]:
    if node.get("WebBookmarkType") == "WebBookmarkTypeLeaf":
        url = node.get("URLString")
        if url:
            yield url
    for child in node.get("Children", []) or []:
        if child.get("Title") in SKIP_TITLES:
            continue
        yield from iter_bookmark_urls(child)


def score_folder(tab: Tab, f: Folder) -> Tuple[float, str]:
    host = _bare_host(tab.host)
    dom = _domain(host)
    score, why = 0.0, ""
    if host in f.hosts:
        score = 10 + min(f.hosts[host], 10)
        why = f"{f.hosts[host]}× {host} schon im Ordner"
    elif dom in f.domains:
        score = 7 + min(f.domains[dom], 10)
        why = f"{f.domains[dom]}× {dom} schon im Ordner"
    elif dom in f.sub_domains:
        # Domain liegt in einem Unterordner – der Unterordner gewinnt dann
        score = 2
        why = f"{dom} in Unterordnern"
    tab_tokens = _tokens(f"{tab.title} {host} {urlsplit(tab.url).path}")
    hits = sorted(f.tokens & tab_tokens)
    if hits:
        score += 4 * len(hits)
        why = why or f"Stichwort „{', '.join(hits)}“"
    kind = tab.kind.lstrip("~")
    if kind and f.tokens & set(KINDS[kind]["folder_words"]):
        bonus = 8 if not tab.kind.startswith("~") else 4
        score += bonus
        label = KINDS[kind]["label"]
        if not why or (bonus >= 8 and score - bonus < 7):
            why = f"{label}-Seite" if bonus >= 8 else f"vermutlich {label}"
    syn = set(CATEGORY_SYNONYMS.get(tab.category, []))
    if tab.category and (f.tokens & syn or f.title.lower() == tab.category.lower()):
        score += 3
        why = why or f"passt zum Thema {tab.category}"
    # Favoriten/Lesezeichenmenü selbst nur bei klaren Domain-Treffern
    if f.depth == 0 and f.title in SPECIAL_TITLES.values() and score < 10:
        score = 0
    # spezifischere (tiefere) Ordner leicht bevorzugen
    if score:
        score += 0.1 * f.depth
    return score, why


def assign_folders(plan: Plan, folders: List[Folder], cfg: Dict) -> None:
    threshold = cfg.get("min_match_score", 3)
    for t in plan.by_action(BOOKMARK):
        best, best_score, best_why = None, 0.0, ""
        for f in folders:
            s, why = score_folder(t, f)
            if s > best_score or (s == best_score and best and f.leaves > best.leaves):
                best, best_score, best_why = f, s, why
        if best and best_score >= threshold:
            t.target_key, t.target_path = best.key, best.path
            t.target_new, t.target_why = False, best_why
        else:
            set_new_target(t, cfg["fallback_folder"], "kein passender Ordner")


def set_new_target(t: Tab, name: str, why: str = "") -> None:
    t.target_key = "new:" + name
    t.target_path = name
    t.target_new = True
    t.target_why = why


# --------------------------------------------------------------------------
# Lesezeichen schreiben
# --------------------------------------------------------------------------
def load_bookmarks(path: Path = BOOKMARKS_PLIST, quiet: bool = False) -> Optional[Dict]:
    try:
        with open(path, "rb") as fh:
            return plistlib.load(fh)
    except FileNotFoundError:
        return None
    except PermissionError:
        if not quiet:
            print("⚠️  Kein Zugriff auf deine Safari-Lesezeichen (Bookmarks.plist).\n"
                  "   Ohne Zugriff kann ich deine Ordner nicht sehen. Bitte erlauben:\n"
                  "   Systemeinstellungen → Datenschutz & Sicherheit → "
                  "Festplattenvollzugriff → Terminal aktivieren, dann Terminal neu starten.\n",
                  file=sys.stderr)
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


def _index_nodes(root: Dict) -> Dict[str, Dict]:
    idx: Dict[str, Dict] = {}

    def walk(node: Dict, prefix: str) -> None:
        for c in node.get("Children", []) or []:
            if c.get("WebBookmarkType") != "WebBookmarkTypeList" \
                    or c.get("Title") in SKIP_TITLES:
                continue
            t = _node_title(c)
            path = f"{prefix}/{t}" if prefix else t
            if c.get("WebBookmarkUUID"):
                idx[c["WebBookmarkUUID"]] = c
            idx.setdefault(path, c)
            walk(c, path)

    walk(root, "")
    return idx


def add_to_existing_folders(root: Dict, tabs: List[Tab], cfg: Dict) -> Dict[str, int]:
    """Fügt Tabs in ihre Zielordner ein. Gibt {Ordnerpfad: Anzahl} zurück."""
    tracking = cfg["tracking_params"]
    existing = {normalize_url(u, tracking) for u in iter_bookmark_urls(root)}
    idx = _index_nodes(root)
    children = root.setdefault("Children", [])
    result: Dict[str, int] = {}
    for t in tabs:
        url = clean_url(t.url, tracking)
        key = normalize_url(url, tracking)
        if key in existing:
            continue
        node = None if t.target_new else idx.get(t.target_key) or idx.get(t.target_path)
        if node is None:
            # neuen Ordner auf oberster Ebene anlegen (bzw. gleichnamigen wiederverwenden)
            node = idx.get(t.target_path)
            if node is None:
                node = _new_folder(t.target_path)
                pos = max((i + 1 for i, c in enumerate(children)
                           if c.get("Title") in SPECIAL_TITLES), default=0)
                children.insert(pos, node)
                idx[t.target_path] = node
        node.setdefault("Children", []).append(_new_leaf(t.title, url))
        existing.add(key)
        result[t.target_path] = result.get(t.target_path, 0) + 1
    return result


def write_bookmarks_plist(tabs: List[Tab], cfg: Dict,
                          path: Path = BOOKMARKS_PLIST) -> Tuple[Dict[str, int], Path]:
    with open(path, "rb") as fh:
        root = plistlib.load(fh)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"Bookmarks.plist.backup-{stamp}")
    shutil.copy2(path, backup)
    result = add_to_existing_folders(root, tabs, cfg)
    tmp = path.with_suffix(".plist.tmp")
    with open(tmp, "wb") as fh:
        plistlib.dump(root, fh, fmt=plistlib.FMT_BINARY)
    os.replace(tmp, path)
    return result, backup


def export_html(tabs: List[Tab], cfg: Dict, out: Path) -> int:
    """Netscape-Bookmark-Datei als Notlösung/Backup, gruppiert nach Zielordner."""
    tracking = cfg["tracking_params"]
    now = int(time.time())
    groups: Dict[str, List[Tab]] = {}
    for t in tabs:
        groups.setdefault(t.target_path or t.category or "Sonstiges", []).append(t)
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>",
    ]
    count = 0
    for name in sorted(groups):
        lines.append(f'    <DT><H3 ADD_DATE="{now}">{html.escape(name)}</H3>')
        lines.append("    <DL><p>")
        for t in groups[name]:
            url = clean_url(t.url, tracking)
            lines.append(f'        <DT><A HREF="{html.escape(url, quote=True)}" '
                         f'ADD_DATE="{now}">{html.escape(t.title or url)}</A>')
            count += 1
        lines.append("    </DL><p>")
    lines += ["</DL><p>", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return count


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------
def _short(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _tw() -> int:
    width = shutil.get_terminal_size((110, 20)).columns
    return max(24, min(48, width - 62))


def _row(t: Tab, info: str) -> str:
    tw = _tw()
    title = (f"[{t.device}] " if t.device else "") + (t.title or t.url)
    return (f"  {t.num:>3}  {_short(title, tw):<{tw}}  "
            f"{_short(_bare_host(t.host), 22):<22}  {info}")


def header(text: str) -> None:
    print(f"\n━━ {text} " + "━" * max(3, 60 - len(text)))


def print_overview(plan: Plan, have_folders: bool) -> None:
    tabs = plan.tabs
    local, remote = split_local_remote(tabs)
    windows = len({t.window for t in local})
    hosts: Dict[str, int] = {}
    for t in tabs:
        if t.host:
            h = _bare_host(t.host)
            hosts[h] = hosts.get(h, 0) + 1
    header("Überblick")
    print(f"  {len(tabs)} Tabs · {len(hosts)} verschiedene Seiten")
    print(f"  Mac: {len(local)} Tabs in {windows} Fenster{'n' if windows != 1 else ''}")
    per_dev: Dict[str, int] = {}
    for t in remote:
        per_dev[t.device] = per_dev.get(t.device, 0) + 1
    for d, n in per_dev.items():
        print(f"  {d}: {n} Tab{'s' if n != 1 else ''} (über iCloud)")
    top = sorted(hosts.items(), key=lambda x: -x[1])[:6]
    if top:
        print("  Am häufigsten: " + ", ".join(f"{h} ({n})" for h, n in top))
    reasons: Dict[str, int] = {}
    for t in plan.by_action(CLOSE):
        r = re.sub(r" (von #\d+|in .+|\(#\d+\))$", "", t.reason)
        reasons[r] = reasons.get(r, 0) + 1
    if reasons:
        print("  Überflüssig: " + ", ".join(f"{n}× {r}" for r, n in
                                            sorted(reasons.items(), key=lambda x: -x[1])))
    print_close_list(plan)
    print_bookmark_list(plan, have_folders)
    keep = plan.by_action(KEEP)
    if keep:
        header(f"Bleibt offen ({len(keep)})")
        for t in keep:
            print(_row(t, t.reason))
    c, b, k = (len(plan.by_action(a)) for a in (CLOSE, BOOKMARK, KEEP))
    print(f"\n  Empfehlung: {c} schließen · {b} in Lesezeichen sichern · {k} offen lassen")


def print_close_list(plan: Plan) -> None:
    items = plan.by_action(CLOSE)
    header(f"Empfehlung: schließen ({len(items)})")
    if not items:
        print("  – nichts –")
    for t in items:
        print(_row(t, t.reason))


def print_remote_close_hint(tabs: List[Tab]) -> None:
    """iPhone-/iPad-Tabs lassen sich nicht automatisch schließen → Checkliste."""
    by_dev: Dict[str, List[Tab]] = {}
    for t in tabs:
        by_dev.setdefault(t.device, []).append(t)
    for dev, items in by_dev.items():
        header(f"Bitte selbst schließen auf {dev} ({len(items)})")
        print("  (Am iPhone: Tab-Übersicht → Tab nach links wischen. Oder am Mac in der "
              "Tab-Übersicht unter dem Gerät.)")
        for t in items:
            print(f"  ☐ {_short(t.title or t.url, 60)}  –  {_bare_host(t.host)}")


def print_bookmark_list(plan: Plan, have_folders: bool) -> None:
    items = plan.by_action(BOOKMARK)
    header(f"In Lesezeichen sichern ({len(items)})")
    if not items:
        print("  – nichts –")
    for t in sorted(items, key=lambda t: (t.target_new, t.target_path.lower(), t.num)):
        if have_folders and t.target_path:
            dest = f"→ {t.target_path}" + (" (neu)" if t.target_new else "")
            why = f"  [{t.target_why}]" if t.target_why else ""
            print(_row(t, dest + why))
        else:
            print(_row(t, t.category))


def print_folders(folders: List[Folder]) -> None:
    header("Deine Lesezeichen-Ordner")
    for f in folders:
        print(f"  {f.num:>3}  {'  ' * f.depth}{f.title}  ({f.leaves})")


def write_report(plan: Plan, out: Path) -> None:
    lines = [f"# Safari-Tab-Bericht {_dt.datetime.now():%Y-%m-%d %H:%M}", ""]
    for action, head in ((CLOSE, "Empfehlung: schließen"),
                         (BOOKMARK, "In Lesezeichen sichern"),
                         (KEEP, "Offen lassen")):
        items = plan.by_action(action)
        if not items:
            continue
        lines += [f"## {head} ({len(items)})", ""]
        for t in items:
            extra = (f"→ {t.target_path}" if t.target_path else t.category) \
                if action == BOOKMARK else t.reason
            title = (t.title or t.url).replace("[", "(").replace("]", ")")
            lines.append(f"- [{title}]({t.url})" + (f" — {extra}" if extra else ""))
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Interaktive Schritte
# --------------------------------------------------------------------------
def _ask(prompt: str) -> Optional[str]:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _apply_action_tokens(ans: str, plan: Plan, cfg: Dict,
                         folders: List[Folder]) -> bool:
    by_num = {t.num: t for t in plan.tabs}
    ok = True
    for tok in ans.replace(",", " ").split():
        mm = re.match(r"^(\d+)(?:-(\d+))?([slb])$", tok, re.I)
        if not mm:
            print(f"  ? „{tok}“ nicht verstanden")
            ok = False
            continue
        a, b = int(mm.group(1)), int(mm.group(2) or mm.group(1))
        for n in range(a, b + 1):
            t = by_num.get(n)
            if not t:
                continue
            t.action = ACTION_KEY[mm.group(3).lower()]
            t.reason = "manuell"
            if t.action == BOOKMARK and not t.target_path:
                t.category = t.category or categorize(t, cfg["categories"])
                if folders:
                    one = Plan([t])
                    assign_folders(one, folders, cfg)
    return ok


def step_close(plan: Plan, cfg: Dict, folders: List[Folder]) -> Optional[bool]:
    """True = schließen, False = überspringen, None = abbrechen"""
    while True:
        loc, rem = split_local_remote(plan.by_action(CLOSE))
        extra = (f" (+ {len(rem)} auf anderen Geräten – dafür bekommst du eine Liste)"
                 if rem else "")
        print(f"\nSchritt 1/2 · {len(loc)} empfohlene Tabs auf dem Mac schließen?{extra}")
        print("  Enter/j = ja · n = nicht schließen, weiter · q = abbrechen\n"
              "  ändern: '12b' Tab 12 behalten, '5l' als Lesezeichen, '7s' schließen, "
              "'3-6b' Bereich")
        ans = _ask("> ")
        if ans is None or ans.lower() == "q":
            return None
        if ans.lower() in ("", "j", "ja", "y"):
            return True
        if ans.lower() in ("n", "nein"):
            return False
        _apply_action_tokens(ans, plan, cfg, folders)
        print_close_list(plan)


def step_bookmarks(plan: Plan, cfg: Dict, folders: List[Folder]) -> Optional[bool]:
    by_num = {t.num: t for t in plan.tabs}
    by_fnum = {f.num: f for f in folders}
    while True:
        n = len(plan.by_action(BOOKMARK))
        print(f"\nSchritt 2/2 · {n} Tabs in deine Lesezeichen-Ordner einsortieren?")
        print("  Enter/j = ja · n = nicht speichern · q = abbrechen\n"
              "  ändern: 'o' Ordnerliste zeigen · '4>12' Tab 4 in Ordner 12 · "
              "'4>Neuer Name' neuer Ordner · '4x' Tab 4 nicht speichern")
        ans = _ask("> ")
        if ans is None or ans.lower() == "q":
            return None
        if ans.lower() in ("", "j", "ja", "y"):
            return True
        if ans.lower() in ("n", "nein"):
            return False
        if ans.lower() in ("o", "ordner"):
            print_folders(folders)
            continue
        for part in re.split(r"\s*[,;]\s*|\s+(?=\d+(?:-\d+)?(?:>|x\b))", ans):
            m = re.match(r"^(\d+)(?:-(\d+))?\s*(?:>\s*(.+)|(x))$", part.strip(), re.I)
            if not m:
                print(f"  ? „{part}“ nicht verstanden")
                continue
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            for i in range(a, b + 1):
                t = by_num.get(i)
                if not t:
                    continue
                if m.group(4):
                    t.action, t.reason = KEEP, "manuell"
                    continue
                dest = m.group(3).strip()
                t.action = BOOKMARK
                if dest.isdigit() and int(dest) in by_fnum:
                    f = by_fnum[int(dest)]
                    t.target_key, t.target_path = f.key, f.path
                    t.target_new, t.target_why = False, "manuell"
                else:
                    dl = dest.lower()
                    existing = next((f for f in folders if dl in
                                     (f.path.lower(), f.title.lower())), None)
                    if existing is None:
                        # eindeutiger Teiltreffer, z. B. "musik" → "Musik & Videos"
                        partial = [f for f in folders if dl in f.title.lower()]
                        existing = partial[0] if len(partial) == 1 else None
                    if existing:
                        t.target_key, t.target_path = existing.key, existing.path
                        t.target_new, t.target_why = False, "manuell"
                    else:
                        set_new_target(t, dest, "manuell")
        print_bookmark_list(plan, bool(folders))


# --------------------------------------------------------------------------
# Safari kurz beenden, Lesezeichen schreiben, Safari wieder öffnen
# --------------------------------------------------------------------------
def save_into_safari(tabs_to_save: List[Tab], cfg: Dict) -> bool:
    remaining = [t.url for t in read_safari_tabs() if not is_empty(t)]
    print("\nSafari wird kurz beendet, damit die Lesezeichen sicher eingetragen werden …")
    osascript("function run(){ Application('Safari').quit(); }")
    for _ in range(60):
        if not safari_running():
            break
        time.sleep(0.25)
    else:
        print("⚠️  Safari hat sich nicht beendet – Lesezeichen nicht geschrieben.",
              file=sys.stderr)
        return False
    time.sleep(0.5)
    ok = True
    try:
        result, backup = write_bookmarks_plist(tabs_to_save, cfg)
        total = sum(result.values())
        print(f"★ {total} Lesezeichen eingetragen (Sicherung: {backup.name})")
        for path, n in sorted(result.items()):
            print(f"    {path}: +{n}")
        if total < len(tabs_to_save):
            print(f"    ({len(tabs_to_save) - total} waren schon vorhanden)")
    except PermissionError:
        ok = False
        print("⚠️  Kein Schreibzugriff auf Bookmarks.plist – Terminal braucht "
              "Festplattenvollzugriff.", file=sys.stderr)
    finally:
        subprocess.run(["open", "-a", "Safari"])
        time.sleep(3)
        restore_missing(remaining)
    return ok


def restore_missing(urls: List[str]) -> None:
    """Öffnet Tabs wieder, falls Safari die letzten Fenster nicht wiederhergestellt hat."""
    if not urls:
        return
    now: set = set()
    for _ in range(5):
        try:
            now = {normalize_url(t.url) for t in read_safari_tabs()}
        except SystemExit:
            now = set()
        if now:
            break
        time.sleep(1)
    missing = [u for u in urls if normalize_url(u) not in now]
    if len(missing) > len(urls) / 2:
        osascript(JXA_OPEN, json.dumps(missing))
        print(f"↺ {len(missing)} offene Tabs wiederhergestellt.")


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
        description="Zeigt einen Überblick über deine Safari-Tabs, empfiehlt welche "
                    "geschlossen werden können, und sortiert die übrigen in deine "
                    "vorhandenen Lesezeichen-Ordner ein.",
    )
    ap.add_argument("-u", "--overview", "-n", "--dry-run", dest="overview",
                    action="store_true",
                    help="nur Überblick und Empfehlung anzeigen, nichts ändern")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="Empfehlung ohne Rückfragen umsetzen")
    ap.add_argument("--close-saved", action="store_true",
                    help="Tabs nach dem Speichern als Lesezeichen auch schließen")
    ap.add_argument("--fallback", metavar="NAME",
                    help="Ordner für Tabs ohne passenden Ordner (Standard: Unsortiert)")
    ap.add_argument("--report", metavar="DATEI", help="Überblick als Markdown speichern")
    ap.add_argument("--export", metavar="DATEI",
                    help="zusätzlich eine Lesezeichen-HTML-Datei schreiben")
    ap.add_argument("--config", metavar="DATEI", help="eigene Regeln (JSON)")
    ap.add_argument("--dump-config", action="store_true",
                    help="Standard-Konfiguration ausgeben und beenden")
    ap.add_argument("--bookmarks", metavar="PLIST",
                    help="andere Bookmarks.plist verwenden (Test)")
    ap.add_argument("--from-json", metavar="DATEI",
                    help="Tabs aus JSON-Datei statt aus Safari lesen (Test)")
    ap.add_argument("--json", action="store_true",
                    help="Analyse als JSON ausgeben und beenden")
    ap.add_argument("--nur-mac", action="store_true",
                    help="Tabs von iPhone/iPad (iCloud) nicht einbeziehen")
    ap.add_argument("--cloud-db", metavar="DB",
                    help="andere CloudTabs.db verwenden (Test)")
    args = ap.parse_args(argv)

    if args.dump_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
        return 0

    cfg = load_config(args.config)
    if args.fallback:
        cfg["fallback_folder"] = args.fallback

    offline = bool(args.from_json)
    if offline:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        tabs = [Tab(window=d.get("window", 1), index=d.get("index", i + 1),
                    title=d.get("title", ""), url=d.get("url", ""))
                for i, d in enumerate(data)]
        if args.cloud_db:
            remote, _ = read_cloud_tabs(Path(args.cloud_db))
            tabs += remote
    else:
        tabs, _, note = read_all_tabs(include_cloud=not args.nur_mac)
        if note:
            print(f"ℹ️  {note}", file=sys.stderr)
    if not tabs:
        print("Keine Tabs gefunden.")
        return 0

    plist_path = Path(args.bookmarks).expanduser() if args.bookmarks else BOOKMARKS_PLIST
    root = load_bookmarks(plist_path)
    folders = collect_folders(root) if root else []
    plan = analyze(tabs, cfg, bookmark_index(root, cfg["tracking_params"]))
    if folders:
        assign_folders(plan, folders, cfg)

    if args.json:
        print(json.dumps([t.__dict__ for t in plan.tabs], indent=2, ensure_ascii=False))
        return 0

    print_overview(plan, bool(folders))
    if args.report:
        write_report(plan, Path(args.report).expanduser())
        print(f"\nBericht gespeichert: {args.report}")
    if args.overview:
        return 0

    # ---- Schritt 1: schließen --------------------------------------------
    do_close = True if args.yes else step_close(plan, cfg, folders)
    if do_close is None:
        print("Abgebrochen – nichts geändert.")
        return 1
    if do_close:
        to_close, remote_close = split_local_remote(plan.by_action(CLOSE))
        if remote_close:
            print_remote_close_hint(remote_close)
        if offline:
            print(f"(Test) würde {len(to_close)} Tabs schließen.")
        elif to_close:
            res = close_tabs(to_close)
            print(f"✖ {res['closed']} Tabs geschlossen"
                  + (f", {res['skipped']} übersprungen (inzwischen verändert)"
                     if res["skipped"] else ""))

    # ---- Schritt 2: in Lesezeichen-Ordner einsortieren -------------------
    if not plan.by_action(BOOKMARK):
        print("Keine Tabs zum Speichern.")
        return 0
    if not folders:
        print("\nOhne Zugriff auf deine Lesezeichen kann ich nicht in vorhandene Ordner "
              "einsortieren.")
    do_save = True if args.yes else step_bookmarks(plan, cfg, folders)
    if do_save is None:
        print("Abgebrochen – Lesezeichen nicht geändert.")
        return 1
    if not do_save:
        return 0
    to_save = plan.by_action(BOOKMARK)

    if args.export or not folders:
        out = Path(args.export).expanduser() if args.export else default_export_path()
        n = export_html(to_save, cfg, out)
        print(f"Lesezeichen-Datei ({n}): {out}\n"
              "  Safari: Ablage → Importieren von → Lesezeichen-HTML-Datei …")

    if folders:
        if offline:
            # Test: in die angegebene plist schreiben (nur mit --bookmarks)
            if args.bookmarks:
                result, backup = write_bookmarks_plist(to_save, cfg, plist_path)
                print(f"★ {sum(result.values())} Lesezeichen eingetragen: "
                      + ", ".join(f"{p} +{n}" for p, n in sorted(result.items())))
            else:
                print(f"(Test) würde {len(to_save)} Lesezeichen eintragen.")
        else:
            if not save_into_safari(to_save, cfg):
                return 1

    if args.close_saved and not offline:
        res = close_tabs([t for t in read_safari_tabs()
                          if normalize_url(t.url) in {normalize_url(s.url) for s in to_save}])
        print(f"✖ {res['closed']} gespeicherte Tabs geschlossen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
