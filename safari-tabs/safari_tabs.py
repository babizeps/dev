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
import base64
import hashlib
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
    # Ordner für Tabs, die zu keinem vorhandenen Ordner passen. None = kein
    # Sammelordner: solche Tabs bekommen keinen Vorschlag und müssen zugeordnet
    # werden (oder bleiben offen).
    "fallback_folder": None,
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
    target_score: float = 0.0  # wie sicher die Ordner-Zuordnung ist
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


def read_all_tabs(include_cloud: bool = True, cloud_db: Optional[Path] = None
                  ) -> Tuple[List[Tab], List[Dict], Optional[str]]:
    """Mac-Tabs + (optional) iCloud-Tabs. Gibt (Tabs, Geräte, Hinweis) zurück."""
    tabs = read_safari_tabs()
    if not include_cloud:
        return tabs, [], None
    try:
        remote, devices = read_cloud_tabs(cloud_db, exclude_devices=[local_computer_name()])
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
            t.target_score = best_score
        elif cfg.get("fallback_folder"):
            set_new_target(t, cfg["fallback_folder"], "kein passender Ordner")
        else:
            t.target_key = t.target_path = ""
            t.target_new, t.target_why = False, "kein passender Ordner – bitte zuordnen"


class AmbiguousFolder(ValueError):
    pass


def find_folder(name: str, folders: List[Folder], partial: bool = True) -> Optional[Folder]:
    """Ordner per Pfad, Pfad-Ende („Video/Musik“), Name oder eindeutigem Teilnamen."""
    n = name.strip().strip("/")
    if n.lower().endswith(" (neu)"):
        n = n[:-6].strip()
    low = n.lower()
    if not low:
        return None
    for f in folders:
        if f.path.lower() == low:
            return f
    hits = [f for f in folders if f.path.lower().endswith("/" + low)
            or ("/" not in low and f.title.lower() == low)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise AmbiguousFolder(f"Ordner „{n}“ ist mehrdeutig: "
                              + ", ".join(f.path for f in hits) + " – bitte den Pfad angeben.")
    if partial and "/" not in low:
        part = [f for f in folders if low in f.title.lower()]
        if len(part) == 1:
            return part[0]
    return None


def resolve_target(dest: str, folders: List[Folder]) -> Tuple[Optional[Folder], Optional[str]]:
    """(vorhandener Ordner, None) oder (None, Pfad des neu anzulegenden Ordners).

    „Video/Musik“ → existiert „Lesezeichenmenü/Video“, aber kein „Musik“ darin,
    wird „Lesezeichenmenü/Video/Musik“ als neuer Unterordner angelegt.
    """
    d = dest.strip().strip("/")
    if d.lower().endswith(" (neu)"):
        d = d[:-6].strip()
    f = find_folder(d, folders)
    if f:
        return f, None
    parts = [p.strip() for p in d.split("/") if p.strip()]
    for i in range(len(parts) - 1, 0, -1):
        parent = find_folder("/".join(parts[:i]), folders)
        if parent:
            return None, parent.path + "/" + "/".join(parts[i:])
    return None, "/".join(parts)


TITLE_STOPWORDS = {
    # Deutsch
    "der", "die", "das", "und", "oder", "für", "mit", "von", "den", "dem", "des", "ein",
    "eine", "einen", "ist", "sind", "wie", "was", "warum", "auf", "aus", "bei", "zum",
    "zur", "nicht", "auch", "nach", "über", "unter", "mehr", "neue", "neuen", "alle",
    "dein", "deine", "ihre", "euer", "sich", "wird", "werden", "kann", "hier", "jetzt",
    "heute", "online", "kaufen", "teil",
    # Englisch
    "the", "and", "for", "with", "from", "your", "you", "how", "what", "why", "this",
    "that", "are", "was", "will", "can", "into", "about", "best", "new", "all", "more",
    "guide", "official", "video", "videos", "home", "page", "free", "part", "episode",
    # Seitennamen
    "youtube", "github", "reddit", "amazon", "medium", "substack", "google", "wikipedia",
    "news", "blog", "www", "com", "html",
}


def _title_words(text: str) -> set:
    return {w for w in re.findall(r"[a-zäöüß][a-zäöüß0-9+#-]{2,}", (text or "").lower())
            if w not in TITLE_STOPWORDS and not w.isdigit()}


def subfolder_hints(plan: Plan, folders: List[Folder], root: Optional[Dict],
                    min_tabs: int = 3) -> List[Dict]:
    """Gruppiert die Tabs je Zielordner nach gemeinsamer Website und häufigen Wörtern –
    als Grundlage für Unterordner-Vorschläge. Vorhandene Lesezeichen im Ordner zählen mit."""
    by_folder: Dict[str, List[Tab]] = {}
    for t in plan.by_action(BOOKMARK):
        if t.target_path:
            by_folder.setdefault(t.target_path, []).append(t)
    existing: Dict[str, List[Tuple[str, str]]] = {}
    if root:
        for _, leaf, path in iter_leaves_with_path(root):
            existing.setdefault(path, []).append((_leaf_title(leaf), leaf.get("URLString", "")))
    out = []
    for path, tabs in sorted(by_folder.items(), key=lambda x: -len(x[1])):
        if len(tabs) < min_tabs:
            continue
        subs = sorted({f.path[len(path) + 1:].split("/")[0] for f in folders
                       if f.path.startswith(path + "/")})
        sites: Dict[str, List[int]] = {}
        words: Dict[str, List[int]] = {}
        for t in tabs:
            h = _bare_host(t.host)
            sites.setdefault(h, []).append(t.num)
            for w in _title_words(t.title) - _tokens(h):
                words.setdefault(w, []).append(t.num)
        old_words: Dict[str, int] = {}
        for title, _url in existing.get(path, []):
            for w in _title_words(title):
                old_words[w] = old_words.get(w, 0) + 1
        out.append({
            "ordner": path,
            "vorhandene_unterordner": subs,
            "tabs": [{"nr": t.num, "titel": t.title, "seite": _bare_host(t.host)} for t in tabs],
            "gemeinsame_seiten": {h: n for h, n in sorted(sites.items(), key=lambda x: -len(x[1]))
                                  if len(n) >= 2},
            "haeufige_woerter": {w: n for w, n in sorted(words.items(), key=lambda x: -len(x[1]))
                                 if len(n) >= 2},
            "vorhandene_lesezeichen": len(existing.get(path, [])),
            "haeufige_woerter_vorhandene": dict(sorted(
                ((w, n) for w, n in old_words.items() if n >= 3), key=lambda x: -x[1])[:15]),
        })
    return out


def structure_hints(plan: Optional[Plan], root: Dict, folder_path: str,
                    include_existing: bool = True, max_items: int = 400) -> Dict:
    """Alles, was Claude braucht, um für einen Ordner eine verschachtelte Struktur zu
    entwerfen: neue Tabs (nr), vorhandene Lesezeichen (id, aktueller Unterordner),
    vorhandene Unterordner-Struktur, gemeinsame Websites und Stichwörter."""
    idx = _index_nodes(root)
    base = idx.get(folder_path)
    if base is None:
        raise FileNotFoundError(f"Ordner „{folder_path}“ nicht gefunden")
    items: List[Dict] = []
    tree: List[str] = []

    def walk(n: Dict, rel: str) -> None:
        for c in n.get("Children", []) or []:
            if c.get("WebBookmarkType") == "WebBookmarkTypeLeaf" and include_existing:
                items.append({"id": c.get("WebBookmarkUUID"), "titel": _leaf_title(c)[:90],
                              "seite": _bare_host(urlsplit(c.get("URLString", "")).hostname or ""),
                              "jetzt_in": rel or "."})
            elif c.get("WebBookmarkType") == "WebBookmarkTypeList":
                sub = f"{rel}/{_node_title(c)}" if rel else _node_title(c)
                tree.append(sub)
                walk(c, sub)
    walk(base, "")
    if plan:
        for t in plan.by_action(BOOKMARK):
            if t.target_path == folder_path or t.target_path.startswith(folder_path + "/"):
                items.append({"nr": t.num, "titel": (t.title or "")[:90],
                              "seite": _bare_host(t.host), "neu": True})
    sites: Dict[str, int] = {}
    words: Dict[str, int] = {}
    for it in items:
        sites[it["seite"]] = sites.get(it["seite"], 0) + 1
        for w in _title_words(it["titel"]) - _tokens(it["seite"]):
            words[w] = words.get(w, 0) + 1
    truncated = len(items) > max_items
    return {
        "ordner": folder_path,
        "vorhandene_unterordner": tree,
        "anzahl": len(items),
        "eintraege": items[:max_items],
        "gekuerzt": truncated,
        "haeufige_seiten": dict(sorted(((k, v) for k, v in sites.items() if v >= 2),
                                       key=lambda x: -x[1])[:25]),
        "haeufige_woerter": dict(sorted(((k, v) for k, v in words.items() if v >= 2),
                                        key=lambda x: -x[1])[:40]),
    }


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
                  "Festplattenvollzugriff → Terminal aktivieren, dann Terminal neu starten.\n"
                  "   Startest du das Tool aus einer anderen App, braucht stattdessen dieses\n"
                  f"   Programm die Freigabe: {python_app_to_allow()}\n",
                  file=sys.stderr)
        return None


# --------------------------------------------------------------------------
# Zugriffsrechte prüfen (Festplattenvollzugriff)
# --------------------------------------------------------------------------
FDA_SETTINGS_URL = ("x-apple.systempreferences:com.apple.preference.security"
                    "?Privacy_AllFiles")


def _ps(pid: int) -> Tuple[int, str]:
    """(Eltern-PID, Programmpfad) eines Prozesses."""
    try:
        out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        ppid, comm = out.split(None, 1)
        return int(ppid), comm.strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0, ""


def _app_bundle(path: str) -> Optional[str]:
    if ".app/" in path:
        return path[: path.index(".app/") + 4]
    return None


def python_app_to_allow() -> str:
    """Das Programm, das macOS beim Dateizugriff tatsächlich prüft.

    Beim Python von Apple (Entwicklerwerkzeuge) und von python.org ist das
    „Python.app“ im Framework – nicht /usr/bin/python3 und nicht die Claude-App.
    """
    _, own = _ps(os.getpid())
    for cand in (own, os.path.realpath(sys.executable)):
        b = _app_bundle(cand or "")
        if b:
            return b
    fw = Path(sys.base_prefix) / "Resources" / "Python.app"
    if fw.exists():
        return str(fw)
    return os.path.realpath(sys.executable)


def _probe(path: Path) -> str:
    try:
        with open(path, "rb") as fh:
            fh.read(16)
        return "ok"
    except FileNotFoundError:
        return "nicht vorhanden"
    except OSError as e:
        if e.errno == 1:
            return "gesperrt (macOS-Datenschutz, Festplattenvollzugriff fehlt)"
        return f"gesperrt ({e.strerror})"


def access_diagnosis() -> Dict:
    chain = []
    pid = os.getpid()
    for _ in range(6):
        ppid, comm = _ps(pid)
        if not comm:
            break
        chain.append(comm)
        if ppid <= 1:
            break
        pid = ppid
    cloud = next((p for p in CLOUD_TABS_DBS if p.exists()), CLOUD_TABS_DBS[0])
    app = python_app_to_allow()
    return {
        "lesezeichen": _probe(BOOKMARKS_PLIST),
        "icloud_tabs": _probe(cloud),
        "python_programm": app,
        "python_version": sys.version.split()[0],
        "gestartet_von": chain,
        "anleitung": [
            "Systemeinstellungen → Datenschutz & Sicherheit → Festplattenvollzugriff öffnen.",
            "Unten auf „+“ klicken, dann ⌘⇧G drücken und diesen Pfad einfügen: " + app,
            "„Öffnen“ klicken und den neuen Eintrag „Python“ einschalten.",
            "Die Claude-App mit ⌘Q komplett beenden und neu öffnen.",
        ],
        "warum": ("Die Erweiterung läuft als eigenes Python-Programm. macOS prüft den "
                  "Festplattenvollzugriff für dieses Programm, deshalb reicht die "
                  "Freigabe für „Claude“ allein nicht."),
    }


# --------------------------------------------------------------------------
# Umweg über Terminal: Wenn das aufrufende Programm (z. B. die Erweiterung in
# der Claude-App) keinen Festplattenvollzugriff bekommt, erledigt Terminal –
# das in der Liste „Festplattenvollzugriff“ freigegeben ist – das Lesen und
# Schreiben der Lesezeichen. Austausch über ~/.safari-tabs/.
# --------------------------------------------------------------------------
BRIDGE_DIR = Path.home() / ".safari-tabs"
BRIDGE_TIMEOUT = 45
TERMINAL_FDA_HINT = (
    "Terminal hat keinen Festplattenvollzugriff. Bitte: Systemeinstellungen → "
    "Datenschutz & Sicherheit → Festplattenvollzugriff → „Terminal“ einschalten "
    "(falls nicht in der Liste: „+“ → Programme → Dienstprogramme → Terminal). "
    "Ein Neustart von Terminal ist nicht nötig, wenn es gerade nicht läuft – "
    "sonst Terminal mit ⌘Q beenden.")


class BridgeError(Exception):
    pass


def run_via_terminal(op: str, payload: Optional[Dict] = None,
                     timeout: float = BRIDGE_TIMEOUT) -> Dict:
    BRIDGE_DIR.mkdir(exist_ok=True)
    token = uuid.uuid4().hex[:12]
    inp = BRIDGE_DIR / f"{token}.in.json"
    out = BRIDGE_DIR / f"{token}.out.json"
    if payload is not None:
        inp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    label = {"copy": "Lesezeichen lesen", "edit": "Lesezeichen ändern",
             "list": "Sicherungen auflisten"}.get(op, op)
    script = BRIDGE_DIR / f"safari-tabs-{op}.command"
    script.write_text(
        "#!/bin/bash\n"
        f'echo "Safari-Tabs: {label} …"\n'
        f'"{sys.executable}" "{Path(__file__).resolve()}" '
        f"--bridge-op {op} --bridge-token {token}\n"
        'echo; echo "Fertig – dieses Fenster kannst du schließen."\n',
        encoding="utf-8")
    script.chmod(0o755)
    subprocess.run(["open", "-a", "Terminal", str(script)])
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            if out.exists():
                time.sleep(0.2)
                res = json.loads(out.read_text(encoding="utf-8"))
                if not res.get("ok"):
                    raise BridgeError(res.get("error") or "Unbekannter Fehler im Terminal")
                return res
            time.sleep(0.3)
        raise BridgeError("Terminal hat nicht rechtzeitig geantwortet. Ist im Terminal-"
                          "Fenster eine Fehlermeldung zu sehen?")
    finally:
        for f in (inp, out):
            try:
                f.unlink()
            except OSError:
                pass


def _tab_to_dict(t: Tab) -> Dict:
    return {"title": t.title, "url": t.url, "target_key": t.target_key,
            "target_path": t.target_path, "target_new": t.target_new}


def bridge_main(op: str, token: str) -> int:
    """Läuft im Terminal (mit dessen Festplattenvollzugriff)."""
    out = BRIDGE_DIR / f"{token}.out.json"
    try:
        if op == "copy":
            shutil.copy2(BOOKMARKS_PLIST, BRIDGE_DIR / "Bookmarks.plist")
            cloud = next((p for p in CLOUD_TABS_DBS if p.exists()), None)
            cdir = BRIDGE_DIR / "cloud"
            if cloud:
                cdir.mkdir(exist_ok=True)
                for suffix in ("", "-wal", "-shm"):
                    f = Path(str(cloud) + suffix)
                    if f.exists():
                        shutil.copy2(f, cdir / (cloud.name + suffix))
            res = {"ok": True, "cloud": bool(cloud)}
            print("✓ Lesezeichen gelesen")
        elif op == "edit":
            data = json.loads((BRIDGE_DIR / f"{token}.in.json").read_text(encoding="utf-8"))
            res = {"ok": True, **edit_bookmarks(data, BOOKMARKS_PLIST)}
            print(f"✓ {res.get('aktion', 'Lesezeichen geändert')}")
        elif op == "list":
            res = {"ok": True, "sicherungen": list_backups(BOOKMARKS_PLIST)}
            print("✓ Sicherungen gelesen")
        else:
            res = {"ok": False, "error": f"unbekannte Aktion {op}"}
    except PermissionError:
        res = {"ok": False, "error": TERMINAL_FDA_HINT}
        print("✗ " + TERMINAL_FDA_HINT)
    except Exception as e:  # noqa: BLE001
        res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print("✗ " + res["error"])
    out.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return 0 if res["ok"] else 1


def load_bookmarks_any(allow_terminal: bool = True
                       ) -> Tuple[Optional[Dict], str, Optional[Path]]:
    """(Lesezeichen, Modus, Pfad der iCloud-Tabs-Kopie). Modus: direkt | terminal | ''."""
    if _probe(BOOKMARKS_PLIST) == "ok":
        return load_bookmarks(BOOKMARKS_PLIST, quiet=True), "direkt", None
    if not allow_terminal or sys.platform != "darwin":
        return None, "", None
    res = run_via_terminal("copy")
    copy = BRIDGE_DIR / "Bookmarks.plist"
    root = load_bookmarks(copy, quiet=True)
    cloud = BRIDGE_DIR / "cloud" / CLOUD_TABS_DBS[0].name if res.get("cloud") else None
    return root, "terminal", cloud


def cleanup_bridge_copies() -> None:
    """Kopien von Lesezeichen/iCloud-Tabs wieder löschen (Datenschutz)."""
    for f in [BRIDGE_DIR / "Bookmarks.plist", *(BRIDGE_DIR / "cloud").glob("*")]:
        try:
            f.unlink()
        except OSError:
            pass


def open_access_settings() -> None:
    """Öffnet die Einstellung Festplattenvollzugriff und zeigt Python.app im Finder."""
    subprocess.run(["open", FDA_SETTINGS_URL])
    app = python_app_to_allow()
    if app.endswith(".app"):
        subprocess.run(["open", "-R", app])


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


def add_to_existing_folders(root: Dict, tabs: List[Tab], cfg: Dict,
                            log: Optional[Dict] = None) -> Dict[str, int]:
    """Fügt Tabs in ihre Zielordner ein. Gibt {Ordnerpfad: Anzahl} zurück.

    log (optional) sammelt, was neu angelegt wurde – für „rückgängig“:
    {"hinzugefuegt": [{id, titel, url, ordner}], "ordner_neu": [{id, titel}]}
    """
    tracking = cfg["tracking_params"]
    existing = {normalize_url(u, tracking) for u in iter_bookmark_urls(root)}
    idx = _index_nodes(root)
    children = root.setdefault("Children", [])
    result: Dict[str, int] = {}
    for t in tabs:
        if not t.target_path:            # ohne Ziel-Ordner wird nichts gespeichert
            continue
        url = clean_url(t.url, tracking)
        key = normalize_url(url, tracking)
        if key in existing:
            continue
        node = None if t.target_new else idx.get(t.target_key) or idx.get(t.target_path)
        if node is None:
            node = idx.get(t.target_path)
        if node is None:
            # neuen Ordner anlegen – bei „Video/Musik“ als Unterordner des
            # längsten vorhandenen Teilpfads, sonst auf oberster Ebene
            parts = [p for p in t.target_path.split("/") if p]
            i = len(parts) - 1
            while i > 0 and "/".join(parts[:i]) not in idx:
                i -= 1
            parent = idx.get("/".join(parts[:i])) if i > 0 else None
            for j in range(i, len(parts)):
                new = _new_folder(parts[j])
                if parent is None:
                    pos = max((k + 1 for k, c in enumerate(children)
                               if c.get("Title") in SPECIAL_TITLES), default=0)
                    children.insert(pos, new)
                else:
                    parent.setdefault("Children", []).append(new)
                sub_path = "/".join(parts[: j + 1])
                idx[sub_path] = new
                if log is not None:
                    log.setdefault("ordner_neu", []).append(
                        {"id": new["WebBookmarkUUID"], "titel": sub_path})
                parent = new
            node = parent
        leaf = _new_leaf(t.title, url)
        node.setdefault("Children", []).append(leaf)
        if log is not None:
            log.setdefault("hinzugefuegt", []).append(
                {"id": leaf["WebBookmarkUUID"], "titel": t.title, "url": url,
                 "ordner": t.target_path})
        existing.add(key)
        result[t.target_path] = result.get(t.target_path, 0) + 1
    return result


# --------------------------------------------------------------------------
# Korrigieren: entfernen, rückgängig machen, Sicherung zurückspielen
# --------------------------------------------------------------------------
BACKUP_RE = re.compile(r"^Bookmarks\.plist\.(backup|vor-wiederherstellung)-\d{8}-\d{6}$")
HISTORY_KEEP = 30


def _history_file() -> Path:
    return BRIDGE_DIR / "verlauf.json"


def load_history() -> List[Dict]:
    try:
        return json.loads(_history_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def append_history(entry: Dict) -> None:
    hist = load_history()
    hist.append(entry)
    BRIDGE_DIR.mkdir(exist_ok=True)
    _history_file().write_text(json.dumps(hist[-HISTORY_KEEP:], ensure_ascii=False, indent=1),
                               encoding="utf-8")


def iter_leaves_with_path(root: Dict) -> Iterable[Tuple[Dict, Dict, str]]:
    """(Elternordner, Lesezeichen, Ordnerpfad) für alle Lesezeichen (ohne Leseliste)."""
    def walk(node: Dict, path: str):
        for c in node.get("Children", []) or []:
            typ = c.get("WebBookmarkType")
            if typ == "WebBookmarkTypeLeaf":
                yield node, c, path
            elif typ == "WebBookmarkTypeList" and c.get("Title") not in SKIP_TITLES:
                t = _node_title(c)
                yield from walk(c, f"{path}/{t}" if path else t)
    yield from walk(root, "")


def _leaf_title(leaf: Dict) -> str:
    return (leaf.get("URIDictionary") or {}).get("title") or leaf.get("Title") or ""


def _folder_matches(want: Optional[str], path: str) -> bool:
    if not want:
        return True
    w = want.strip().strip("/").lower()
    p = path.lower()
    return w == p or w == p.rsplit("/", 1)[-1] or p.endswith("/" + w)


def _leaf_matches(item: Dict, leaf: Dict, path: str, tracking: Iterable[str]) -> bool:
    if item.get("id"):
        return leaf.get("WebBookmarkUUID") == item["id"]
    if not _folder_matches(item.get("ordner"), path):
        return False
    if item.get("url"):
        return normalize_url(leaf.get("URLString", ""), tracking) == \
            normalize_url(item["url"], tracking)
    if item.get("titel") and item.get("ordner"):
        return _leaf_title(leaf).strip().lower() == item["titel"].strip().lower()
    return False


def find_bookmarks(root: Dict, items: List[Dict], cfg: Dict) -> List[Dict]:
    tracking = cfg["tracking_params"]
    out = []
    for _, leaf, path in iter_leaves_with_path(root):
        if any(_leaf_matches(it, leaf, path, tracking) for it in items):
            out.append({"id": leaf.get("WebBookmarkUUID"), "titel": _leaf_title(leaf),
                        "url": leaf.get("URLString"), "ordner": path})
    return out


def search_bookmarks(root: Dict, text: str, folder: Optional[str] = None,
                     limit: int = 50) -> List[Dict]:
    """Volltextsuche in Titel und URL (für Claude, um Einträge zu finden)."""
    q = (text or "").strip().lower()
    out = []
    for _, leaf, path in iter_leaves_with_path(root):
        if not _folder_matches(folder, path):
            continue
        if q and q not in _leaf_title(leaf).lower() and q not in leaf.get("URLString", "").lower():
            continue
        out.append({"id": leaf.get("WebBookmarkUUID"), "titel": _leaf_title(leaf),
                    "url": leaf.get("URLString"), "ordner": path})
        if len(out) >= limit:
            break
    return out


def remove_from_tree(root: Dict, items: List[Dict], cfg: Dict,
                     empty_folder_ids: Iterable[str] = ()) -> List[Dict]:
    """Entfernt passende Lesezeichen. Ordner werden nur entfernt, wenn sie in
    empty_folder_ids stehen (vom Tool angelegt) und danach leer sind."""
    tracking = cfg["tracking_params"]
    hits = [(parent, leaf, path) for parent, leaf, path in iter_leaves_with_path(root)
            if any(_leaf_matches(it, leaf, path, tracking) for it in items)]
    removed = []
    for parent, leaf, path in hits:
        kids = parent.get("Children", [])
        for i, c in enumerate(kids):
            if c is leaf:
                del kids[i]
                removed.append({"id": leaf.get("WebBookmarkUUID"), "titel": _leaf_title(leaf),
                                "url": leaf.get("URLString"), "ordner": path})
                break
    ids = set(empty_folder_ids)
    if ids:
        def prune(node: Dict) -> None:
            kids = node.get("Children", []) or []
            for c in kids:                       # zuerst die Unterordner
                if c.get("WebBookmarkType") == "WebBookmarkTypeList":
                    prune(c)
            node["Children"] = [c for c in kids if not (
                c.get("WebBookmarkType") == "WebBookmarkTypeList"
                and c.get("WebBookmarkUUID") in ids and not c.get("Children"))]
        prune(root)
    return removed


def list_backups(path: Path = None) -> List[Dict]:
    path = path or BOOKMARKS_PLIST
    out = []
    for f in path.parent.glob("Bookmarks.plist.*"):
        if BACKUP_RE.match(f.name):
            st_ = f.stat()
            out.append({"name": f.name, "zeit": _dt.datetime.fromtimestamp(st_.st_mtime)
                        .strftime("%d.%m.%Y %H:%M:%S"), "groesse_kb": st_.st_size // 1024})
    return sorted(out, key=lambda d: d["name"].rsplit("-", 2)[-2:], reverse=True)


# --------------------------------------------------------------------------
# Ordnerstruktur: verschachtelte Unterordner, Verschieben, smarte Sortierung
# --------------------------------------------------------------------------
LAST_FOLDER_NAMES = {"sonstiges", "sonstige", "diverses", "andere", "anderes", "misc",
                     "other", "others", "unsortiert", "allgemein", "general", "rest",
                     "mehr", "more"}


def _natural_key(text: str) -> List:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", (text or "").casefold())]


GENERIC_FOLDER_NAMES = LAST_FOLDER_NAMES | {
    "verschiedenes", "allgemeines", "weitere", "weiteres", "miscellaneous", "stuff", "mix",
    "gemischt", "neu", "new", "temp", "tmp", "unsorted", "sammlung", "kram", "zeug",
    "various", "random", "extras", "extra", "dies und das", "dies & das", "etc", "ordner",
    "folder", "neuer ordner", "new folder", "unbenannt", "untitled", "tabs", "links",
    "lesezeichen", "bookmarks", "zu sortieren", "to sort", "inbox", "eingang",
}
GENERIC_PATTERN = re.compile(r"^(neuer? ordner|new folder|ordner|folder|untitled|unbenannt)"
                             r"\s*\d*$|^(sonstige|andere|weitere|other|misc)\b", re.I)
MIN_PER_FOLDER = 2
MAX_DEPTH = 3


def is_generic_name(name: str) -> bool:
    n = " ".join((name or "").split()).strip().casefold()
    return not n or n in GENERIC_FOLDER_NAMES or bool(GENERIC_PATTERN.search(n))


def _count_leaves(node: Dict) -> int:
    n = 0
    for c in node.get("Children", []) or []:
        if c.get("WebBookmarkType") == "WebBookmarkTypeLeaf":
            n += 1
        elif c.get("WebBookmarkType") == "WebBookmarkTypeList" and c.get("Title") not in SKIP_TITLES:
            n += _count_leaves(c)
    return n


def check_structure(base: Dict, base_path: str, rel_paths: Iterable[str]) -> List[str]:
    """Regeln für (neue/geänderte) Unterordner unterhalb von base:
    • von breit zu spezifisch – kein Ordner, der nur genau einen Unterordner und sonst
      nichts enthält; höchstens MAX_DEPTH Ebenen
    • mindestens MIN_PER_FOLDER Einträge je Ordner (inkl. Unterordner)
    • keine Sammelnamen wie „Sonstiges“, „Misc“, „Allgemein“ …"""
    wanted = set()
    for rel in rel_paths:
        parts = [p for p in (rel or "").split("/") if p.strip()]
        for i in range(1, len(parts) + 1):
            wanted.add("/".join(parts[:i]).casefold())
    problems: List[str] = []

    def walk(node: Dict, rel: str, depth: int) -> None:
        for c in node.get("Children", []) or []:
            if c.get("WebBookmarkType") != "WebBookmarkTypeList" or c.get("Title") in SKIP_TITLES:
                continue
            title = _node_title(c)
            sub = f"{rel}/{title}" if rel else title
            if sub.casefold() in wanted:
                label = f"„{base_path}/{sub}“"
                if is_generic_name(title):
                    problems.append(f"{label}: Sammelname – bitte einen konkreten Namen wählen "
                                    "oder die Einträge thematisch verteilen")
                n = _count_leaves(c)
                if n < MIN_PER_FOLDER:
                    problems.append(f"{label}: nur {n} Eintrag – mindestens {MIN_PER_FOLDER} "
                                    "nötig, sonst eine Ebene höher einordnen")
                kids = c.get("Children", []) or []
                subs = [k for k in kids if k.get("WebBookmarkType") == "WebBookmarkTypeList"]
                direct = [k for k in kids if k.get("WebBookmarkType") == "WebBookmarkTypeLeaf"]
                if len(subs) == 1 and not direct:
                    problems.append(f"{label}: enthält nur den Unterordner „{_node_title(subs[0])}“ "
                                    "– nicht breiter als sein Inhalt; Ebenen zusammenlegen")
                if depth > MAX_DEPTH:
                    problems.append(f"{label}: tiefer als {MAX_DEPTH} Ebenen")
            walk(c, sub, depth + 1)
    walk(base, "", 1)
    return problems


def check_new_folders(tabs: List[Tab]) -> List[str]:
    """Für neu anzulegende Ordner beim Speichern: kein Sammelname, ≥ 2 Tabs je neuem
    Ordner (inkl. neuer Unterordner darin)."""
    counts: Dict[str, int] = {}
    for t in tabs:
        if t.target_new and t.target_path:
            parts = t.target_path.split("/")
            for i in range(1, len(parts) + 1):
                counts["/".join(parts[:i])] = counts.get("/".join(parts[:i]), 0) + 1
    new_paths = {t.target_path for t in tabs if t.target_new}
    problems = []
    for path in sorted(new_paths):
        name = path.rsplit("/", 1)[-1]
        if is_generic_name(name):
            problems.append(f"„{path}“: Sammelname – bitte einen konkreten Namen wählen")
        if counts.get(path, 0) < MIN_PER_FOLDER:
            problems.append(f"„{path}“: nur {counts.get(path, 0)} Tab – ein neuer Ordner braucht "
                            f"mindestens {MIN_PER_FOLDER}; sonst in einen vorhandenen Ordner")
    return problems


def smart_sort(node: Dict, recursive: bool = True) -> None:
    """Unterordner zuerst (alphabetisch, Sammelordner wie „Sonstiges“ zuletzt), danach
    die Lesezeichen nach Website und Titel. Sonderelemente bleiben unberührt."""
    kids = node.get("Children", []) or []
    folders = [c for c in kids if c.get("WebBookmarkType") == "WebBookmarkTypeList"]
    leaves = [c for c in kids if c.get("WebBookmarkType") == "WebBookmarkTypeLeaf"]
    other = [c for c in kids if c not in folders and c not in leaves]
    folders.sort(key=lambda c: (is_generic_name(_node_title(c)),
                                _natural_key(_node_title(c))))
    leaves.sort(key=lambda c: (_domain(urlsplit(c.get("URLString", "")).hostname or ""),
                               _natural_key(_leaf_title(c))))
    node["Children"] = folders + leaves + other
    if recursive:
        for f in folders:
            if f.get("Title") not in SKIP_TITLES:
                smart_sort(f, True)


def _structure_hash(node: Dict) -> str:
    """Fingerabdruck von Aufbau und Inhalt (ohne Sync-Metadaten von iCloud)."""
    def walk(n: Dict):
        return [n.get("WebBookmarkType"), n.get("Title"), n.get("URLString"),
                n.get("WebBookmarkUUID"), [walk(c) for c in n.get("Children", []) or []]]
    return hashlib.sha256(json.dumps(walk(node), ensure_ascii=False).encode()).hexdigest()


def _find_by_uuid(root: Dict, uid: str) -> Optional[Dict]:
    if root.get("WebBookmarkUUID") == uid:
        return root
    for c in root.get("Children", []) or []:
        hit = _find_by_uuid(c, uid)
        if hit is not None:
            return hit
    return None


def _ensure_subfolder(parent: Dict, rel_path: str, created: List[Dict], base_path: str) -> Dict:
    node, path = parent, base_path
    for part in [p.strip() for p in rel_path.split("/") if p.strip()]:
        path = f"{path}/{part}"
        sub = next((c for c in node.get("Children", []) or []
                    if c.get("WebBookmarkType") == "WebBookmarkTypeList"
                    and _node_title(c).strip().casefold() == part.casefold()), None)
        if sub is None:
            sub = _new_folder(part)
            node.setdefault("Children", []).append(sub)
            created.append({"id": sub["WebBookmarkUUID"], "titel": path})
        node = sub
    return node


class StructureError(ValueError):
    def __init__(self, problems: List[str]):
        super().__init__("Struktur verletzt die Regeln:\n• " + "\n• ".join(problems))
        self.problems = problems


def restructure_folder(root: Dict, spec: Dict, cfg: Dict) -> Dict:
    """Baut in einem vorhandenen Ordner eine (verschachtelte) Unterordner-Struktur.

    spec = {"ordner": "Lesezeichenmenü/Video",
            "baum": [{"pfad": "Musik/Lofi", "ids": [Lesezeichen-UUIDs zum Verschieben],
                      "neu": [Tab-Dicts zum Hinzufügen]}],
            "sortieren": True, "leere_entfernen": True}
    Verschoben werden nur Lesezeichen, die schon in diesem Ordner (inkl. Unterordnern)
    liegen. Gibt Protokoll inkl. Schnappschuss für „rückgängig“ zurück.
    """
    tracking = cfg["tracking_params"]
    idx = _index_nodes(root)
    base = idx.get(spec["ordner"])
    if base is None:
        raise FileNotFoundError(f"Ordner „{spec['ordner']}“ nicht gefunden")
    before = base64.b64encode(plistlib.dumps(base, fmt=plistlib.FMT_BINARY)).decode()
    base_path = next(p for p, n in idx.items() if n is base and not re.fullmatch(
        r"[0-9A-F-]{36}", p))

    # alle Lesezeichen im Ordner-Teilbaum: uuid → (Elternordner, Lesezeichen)
    inside: Dict[str, Tuple[Dict, Dict]] = {}
    nonempty_before = set()

    def walk(n: Dict) -> None:
        for c in n.get("Children", []) or []:
            if c.get("WebBookmarkType") == "WebBookmarkTypeLeaf" and c.get("WebBookmarkUUID"):
                inside[c["WebBookmarkUUID"]] = (n, c)
            elif c.get("WebBookmarkType") == "WebBookmarkTypeList":
                if c.get("Children"):
                    nonempty_before.add(id(c))
                walk(c)
    walk(base)
    existing_urls = {normalize_url(u, tracking) for u in iter_bookmark_urls(root)}

    created: List[Dict] = []
    moved: List[Dict] = []
    added: List[Dict] = []
    missing: List[str] = []
    for item in spec.get("baum", []):
        rel = (item.get("pfad") or "").strip().strip("/")
        target = _ensure_subfolder(base, rel, created, base_path) if rel else base
        tpath = f"{base_path}/{rel}" if rel else base_path
        for uid in item.get("ids", []):
            hit = inside.get(uid)
            if not hit:
                missing.append(uid)
                continue
            parent, leaf = hit
            if parent is target:
                continue
            parent["Children"] = [c for c in parent.get("Children", []) if c is not leaf]
            target.setdefault("Children", []).append(leaf)
            inside[uid] = (target, leaf)
            moved.append({"id": uid, "titel": _leaf_title(leaf), "nach": tpath})
        for d in item.get("neu", []):
            url = clean_url(d["url"], tracking)
            key = normalize_url(url, tracking)
            if key in existing_urls:
                continue
            leaf = _new_leaf(d.get("title", ""), url)
            target.setdefault("Children", []).append(leaf)
            existing_urls.add(key)
            added.append({"id": leaf["WebBookmarkUUID"], "titel": d.get("title", ""),
                          "url": url, "ordner": tpath})

    removed_empty: List[str] = []
    if spec.get("leere_entfernen", True):
        def prune(n: Dict, path: str) -> None:
            for c in list(n.get("Children", []) or []):
                if c.get("WebBookmarkType") == "WebBookmarkTypeList":
                    prune(c, f"{path}/{_node_title(c)}")
            keep = []
            for c in n.get("Children", []) or []:
                if (c.get("WebBookmarkType") == "WebBookmarkTypeList" and not c.get("Children")
                        and id(c) in nonempty_before):
                    removed_empty.append(f"{path}/{_node_title(c)}")
                    continue
                keep.append(c)
            n["Children"] = keep
        prune(base, base_path)
    if spec.get("pruefen", True):
        problems = check_structure(base, base_path,
                                   [i.get("pfad", "") for i in spec.get("baum", [])])
        if problems:
            raise StructureError(problems)
    if spec.get("sortieren", True):
        smart_sort(base)
    return {"ordner": base_path, "ordner_id": base.get("WebBookmarkUUID"),
            "ordner_neu": created, "verschoben": moved, "hinzugefuegt": added,
            "leer_entfernt": removed_empty, "nicht_gefunden": missing,
            "vorher": before, "nachher_hash": _structure_hash(base)}


# --- selbständiges Ordnen (ohne Claude): Stichwort-/Website-Gruppen -------------
ORGANIZE_DEFAULTS = {"min_gruppe": 3, "ab": 6, "max_tiefe": MAX_DEPTH, "verschachteln_ab": 8}


def _label_for_word(word: str, titles: List[str]) -> str:
    forms: Dict[str, int] = {}
    for t in titles:
        for m in re.finditer(r"[^\W_][\w+#-]*", t or ""):
            if m.group(0).casefold() == word:
                forms[m.group(0)] = forms.get(m.group(0), 0) + 1
    best = max(forms.items(), key=lambda x: (x[1], x[0][:1].isupper()))[0] if forms else word
    return best if best[:1].isupper() or best.isupper() else best[:1].upper() + best[1:]


def _site_label(host: str) -> str:
    name = _domain(host).split(".")[0]
    return name[:1].upper() + name[1:] if name else ""


def cluster_items(items: List[Dict], used: set, depth: int, opts: Dict) -> Tuple[List[Dict], List[Dict]]:
    """Greedy-Gruppierung nach gemeinsamen Titelwörtern bzw. Websites.
    items: [{id, titel, host, words}] → (Gruppen [{name, items, kinder}], Rest)."""
    min_size = opts["min_gruppe"]
    groups: List[Dict] = []
    remaining = list(items)
    names_used = {u.casefold() for u in used}
    site_total: Dict[str, int] = {}
    for it in items:
        k = _site_label(it["host"]).casefold()
        site_total[k] = site_total.get(k, 0) + 1
    while True:
        cand: Dict[Tuple[str, str], List[Dict]] = {}
        for it in remaining:
            for w in it["words"]:
                if w not in used:
                    cand.setdefault(("w", w), []).append(it)
            site = _site_label(it["host"])
            if site and site.casefold() not in names_used:
                cand.setdefault(("s", site.casefold()), []).append(it)
        best = None
        for (kind, key), members in cand.items():
            n = len(members)
            if n < min_size or n >= len(items):          # alles in einer Gruppe = nichts gewonnen
                continue
            if kind == "s" and site_total[key] > 0.5 * len(items):  # Website prägt den Ordner
                continue
            label = (_label_for_word(key, [m["titel"] for m in members]) if kind == "w"
                     else _site_label(members[0]["host"]))
            if is_generic_name(label) or label.casefold() in names_used or len(label) < 2:
                continue
            score = (kind == "w", n)                     # Thema vor Website
            if best is None or score > best[0]:
                best = (score, kind, key, label, members)
        if not best:
            break
        _, kind, key, label, members = best
        ids = {id(m) for m in members}
        remaining = [r for r in remaining if id(r) not in ids]
        names_used.add(label.casefold())
        groups.append({"name": label, "items": members, "key": key, "kinder": [], "rest": members})
    for g in groups:
        if depth < opts["max_tiefe"] and len(g["items"]) >= opts["verschachteln_ab"]:
            kids, rest = cluster_items(g["items"], used | {g["key"]}, depth + 1, opts)
            # von breit zu spezifisch: nur mit mindestens zwei Untergruppen
            if len(kids) >= 2:
                g["kinder"], g["rest"] = kids, rest
    return groups, remaining


def _baum_from_groups(groups: List[Dict], prefix: str) -> List[Dict]:
    out = []
    for g in groups:
        path = f"{prefix}/{g['name']}" if prefix else g["name"]
        if g["rest"]:
            out.append({"pfad": path, "ids": [m["id"] for m in g["rest"]]})
        out += _baum_from_groups(g["kinder"], path)
    return out


def organize_plan(root: Dict, cfg: Dict, opts: Optional[Dict] = None) -> List[Dict]:
    """Specs für restructure_folder: pro Hauptordner (unter Favoriten/Lesezeichenmenü
    oder auf oberster Ebene) werden lose Lesezeichen – im Ordner selbst und in seinen
    vorhandenen Unterordnern – in neue, thematische Unterordner gruppiert."""
    opts = {**ORGANIZE_DEFAULTS, **(opts or {})}
    tops: List[Tuple[Dict, str]] = []
    for c in root.get("Children", []) or []:
        if c.get("WebBookmarkType") != "WebBookmarkTypeList" or c.get("Title") in SKIP_TITLES:
            continue
        if c.get("Title") in SPECIAL_TITLES:
            for cc in c.get("Children", []) or []:
                if cc.get("WebBookmarkType") == "WebBookmarkTypeList":
                    tops.append((cc, f"{SPECIAL_TITLES[c['Title']]}/{_node_title(cc)}"))
        else:
            tops.append((c, _node_title(c)))
    specs = []
    for node, path in tops:
        baum: List[Dict] = []

        def visit(n: Dict, rel: str, depth: int) -> None:
            leaves = [c for c in n.get("Children", []) or []
                      if c.get("WebBookmarkType") == "WebBookmarkTypeLeaf"]
            subs = [c for c in n.get("Children", []) or []
                    if c.get("WebBookmarkType") == "WebBookmarkTypeList"]
            if len(leaves) >= opts["ab"] and depth < opts["max_tiefe"]:
                used = set()
                for part in [path] + ([rel] if rel else []):
                    used |= _tokens(part.replace("/", " "))
                used |= {_node_title(s_).casefold() for s_ in subs}
                items = [{"id": l.get("WebBookmarkUUID"), "titel": _leaf_title(l),
                          "host": urlsplit(l.get("URLString", "")).hostname or "",
                          "words": _title_words(_leaf_title(l))} for l in leaves
                         if l.get("WebBookmarkUUID")]
                local = dict(opts, max_tiefe=opts["max_tiefe"] - depth)
                groups, _ = cluster_items(items, used, 1, local)
                baum.extend(_baum_from_groups(groups, rel))
            for s_ in subs:
                visit(s_, f"{rel}/{_node_title(s_)}" if rel else _node_title(s_), depth + 1)
        visit(node, "", 0)
        specs.append({"ordner": path, "baum": baum, "sortieren": True, "leere_entfernen": False})
    return specs


def organize_all(root: Dict, cfg: Dict, opts: Optional[Dict] = None) -> List[Dict]:
    results = []
    for spec in organize_plan(root, cfg, opts):
        try:
            results.append(restructure_folder(root, spec, cfg))
        except StructureError:
            # Gruppen verletzen eine Regel → diesen Ordner nur sortieren
            results.append(restructure_folder(root, dict(spec, baum=[]), cfg))
    return results


def describe_organize(root: Dict, cfg: Dict, opts: Optional[Dict] = None) -> List[Dict]:
    """Vorschau (ändert nichts): neue Unterordner und Anzahl je Ordner."""
    trial = copy.deepcopy(root)
    out = []
    for r in organize_all(trial, cfg, opts):
        counts: Dict[str, int] = {}
        for m in r["verschoben"]:
            counts[m["nach"]] = counts.get(m["nach"], 0) + 1
        if r["ordner_neu"] or counts:
            out.append({"ordner": r["ordner"],
                        "neue_unterordner": [o["titel"] for o in r["ordner_neu"]],
                        "verschiebungen": counts})
    return out


def restore_folder_snapshot(root: Dict, snap: Dict, force: bool = False) -> str:
    node = _find_by_uuid(root, snap["ordner_id"]) if snap.get("ordner_id") else None
    if node is None:
        node = _index_nodes(root).get(snap.get("ordner", ""))
    if node is None:
        raise FileNotFoundError("Ordner der Umstrukturierung nicht mehr gefunden")
    if not force and _structure_hash(node) != snap["nachher_hash"]:
        raise ValueError("Der Ordner wurde seitdem verändert – rückgängig machen würde diese "
                         "Änderungen ebenfalls verwerfen. Mit erzwingen=true trotzdem ausführen.")
    old = plistlib.loads(base64.b64decode(snap["vorher"]))
    node.clear()
    node.update(old)
    return snap.get("ordner", "")


def edit_bookmarks(change: Dict, path: Path = None) -> Dict:
    """Führt eine Änderung an Bookmarks.plist aus (Safari muss beendet sein).

    change = {"add": [Tab-Dicts], "remove": [{id}|{url, ordner?}|{titel, ordner}],
              "remove_folder_ids": [...], "restore": "Bookmarks.plist.backup-…",
              "aktion": "Beschreibung für den Verlauf"}
    Vorher wird immer eine Sicherung angelegt.
    """
    path = path or BOOKMARKS_PLIST
    cfg = load_config(None)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    entry: Dict = {"zeit": _dt.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                   "aktion": change.get("aktion", "")}

    if change.get("restore"):
        name = change["restore"]
        if not BACKUP_RE.match(name):
            raise ValueError(f"Ungültiger Sicherungsname: {name}")
        src = path.with_name(name)
        if not src.exists():
            raise FileNotFoundError(f"Sicherung {name} nicht gefunden")
        plistlib.loads(src.read_bytes())          # muss eine gültige plist sein
        before = path.with_name(f"Bookmarks.plist.vor-wiederherstellung-{stamp}")
        shutil.copy2(path, before)
        tmp = path.with_suffix(".plist.tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, path)
        entry.update(aktion=entry["aktion"] or "Sicherung zurückgespielt",
                     wiederhergestellt=name, sicherung=before.name)
        append_history(entry)
        return entry

    with open(path, "rb") as fh:
        root = plistlib.load(fh)
    backup = path.with_name(f"Bookmarks.plist.backup-{stamp}")
    shutil.copy2(path, backup)
    entry["sicherung"] = backup.name
    log: Dict = {"hinzugefuegt": [], "ordner_neu": []}
    for snap in change.get("snapshot_restore", []):
        restore_folder_snapshot(root, snap, change.get("force", False))
        entry["aktion"] = entry["aktion"] or "Ordnerstruktur rückgängig gemacht"
    if change.get("add"):
        tabs = [Tab(window=0, index=0, title=d["title"], url=d["url"], action=BOOKMARK,
                    target_key=d.get("target_key", ""), target_path=d["target_path"],
                    target_new=d.get("target_new", False)) for d in change["add"]
                if d.get("target_path")]
        if change.get("pruefen", True):
            problems = check_new_folders(tabs)
            if problems:
                raise StructureError(problems)
        entry["ergebnis"] = add_to_existing_folders(root, tabs, cfg, log)
        entry["aktion"] = entry["aktion"] or "Lesezeichen hinzugefügt"
    if change.get("remove") or change.get("remove_folder_ids"):
        entry["entfernt"] = remove_from_tree(root, change.get("remove", []), cfg,
                                             change.get("remove_folder_ids", []))
        entry["aktion"] = entry["aktion"] or "Lesezeichen entfernt"
    for spec in change.get("restructure", []):
        res = restructure_folder(root, spec, cfg)
        entry.setdefault("umstrukturiert", []).append(res)
        log["hinzugefuegt"] += res["hinzugefuegt"]
        log["ordner_neu"] += res["ordner_neu"]
        entry["aktion"] = entry["aktion"] or "Ordnerstruktur angelegt"
    if change.get("organize") is not None:
        for res in organize_all(root, cfg, change["organize"]):
            entry.setdefault("umstrukturiert", []).append(res)
        entry["aktion"] = entry["aktion"] or "Alles geordnet"
    for name in change.get("sort", []):
        node = _index_nodes(root).get(name)
        if node is None:
            raise FileNotFoundError(f"Ordner „{name}“ nicht gefunden")
        snap = {"ordner": name, "ordner_id": node.get("WebBookmarkUUID"),
                "vorher": base64.b64encode(plistlib.dumps(node, fmt=plistlib.FMT_BINARY)).decode()}
        smart_sort(node)
        snap["nachher_hash"] = _structure_hash(node)
        entry.setdefault("umstrukturiert", []).append(snap)
        entry["aktion"] = entry["aktion"] or f"„{name}“ sortiert"
    entry.update(log)
    tmp = path.with_suffix(".plist.tmp")
    with open(tmp, "wb") as fh:
        plistlib.dump(root, fh, fmt=plistlib.FMT_BINARY)
    os.replace(tmp, path)
    append_history(entry)
    return entry


def undo_change_for(entry: Dict, force: bool = False) -> Dict:
    """Änderung, die einen Verlaufseintrag rückgängig macht."""
    label = f"Rückgängig: {entry.get('aktion', '')} vom {entry.get('zeit', '')}"
    if entry.get("umstrukturiert"):
        # Ordner auf den Stand davor zurücksetzen; Lesezeichen, die außerhalb
        # dieser Ordner hinzugefügt wurden, zusätzlich entfernen
        inside = {a["id"] for r in entry["umstrukturiert"] for a in r.get("hinzugefuegt", [])}
        return {"snapshot_restore": [
                    {k: r[k] for k in ("ordner", "ordner_id", "vorher", "nachher_hash") if k in r}
                    for r in reversed(entry["umstrukturiert"])],
                "remove": [{"id": a["id"]} for a in entry.get("hinzugefuegt", [])
                           if a["id"] not in inside],
                "force": force, "aktion": label}
    return {"remove": [{"id": a["id"]} for a in entry.get("hinzugefuegt", [])],
            "remove_folder_ids": [f["id"] for f in entry.get("ordner_neu", [])],
            "aktion": label}


def last_undoable() -> Optional[Dict]:
    for e in reversed(load_history()):
        if e.get("rueckgaengig_gemacht") or e.get("aktion", "").startswith("Rückgängig"):
            continue
        if e.get("hinzugefuegt") or e.get("umstrukturiert"):
            return e
    return None


def mark_undone(entry: Dict) -> None:
    hist = load_history()
    for e in hist:
        if e.get("zeit") == entry.get("zeit") and e.get("sicherung") == entry.get("sicherung"):
            e["rueckgaengig_gemacht"] = True
    BRIDGE_DIR.mkdir(exist_ok=True)
    _history_file().write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")


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
              "'4>Neuer Name' neuer Ordner · '4>Video/Musik' Unterordner · "
              "'4x' Tab 4 nicht speichern")
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
                    try:
                        existing, new_path = resolve_target(dest, folders)
                    except AmbiguousFolder as e:
                        print(f"  ? {e}")
                        continue
                    if existing:
                        t.target_key, t.target_path = existing.key, existing.path
                        t.target_new, t.target_why = False, "manuell"
                    else:
                        set_new_target(t, new_path, "manuell")
        print_bookmark_list(plan, bool(folders))


# --------------------------------------------------------------------------
# Safari kurz beenden, Lesezeichen schreiben, Safari wieder öffnen
# --------------------------------------------------------------------------
def apply_bookmark_change(change: Dict, via_terminal: Optional[bool] = None) -> Dict:
    """Safari beenden → Änderung ausführen (direkt oder über Terminal) → Safari öffnen.

    Gibt {"ok": True, …Verlaufseintrag} oder {"ok": False, "fehler": …} zurück.
    """
    if via_terminal is None:
        via_terminal = _probe(BOOKMARKS_PLIST) != "ok"
    was_running = safari_running()
    remaining: List[str] = []
    if was_running:
        remaining = [t.url for t in read_safari_tabs() if not is_empty(t)]
        print("Safari wird kurz beendet, damit die Lesezeichen sicher geändert werden …")
        osascript("function run(){ Application('Safari').quit(); }")
        for _ in range(60):
            if not safari_running():
                break
            time.sleep(0.25)
        else:
            return {"ok": False, "fehler": "Safari hat sich nicht beendet – nichts geändert."}
        time.sleep(0.5)
    try:
        try:
            if via_terminal:
                raise PermissionError
            return {"ok": True, **edit_bookmarks(change, BOOKMARKS_PLIST)}
        except PermissionError:
            if sys.platform != "darwin":
                raise
            print("Kein direkter Zugriff – Änderung läuft über Terminal …")
            res = run_via_terminal("edit", change)
            res.pop("error", None)
            return res
    except PermissionError:
        return {"ok": False, "fehler": TERMINAL_FDA_HINT}
    except (BridgeError, ValueError, FileNotFoundError) as e:
        return {"ok": False, "fehler": str(e)}
    finally:
        if was_running:
            subprocess.run(["open", "-a", "Safari"])
            time.sleep(3)
            restore_missing(remaining)


def save_into_safari(tabs_to_save: List[Tab], cfg: Dict,
                     via_terminal: Optional[bool] = None) -> bool:
    res = apply_bookmark_change({"add": [_tab_to_dict(t) for t in tabs_to_save]},
                                via_terminal)
    if not res.get("ok"):
        print(f"⚠️  {res.get('fehler')}")
        return False
    result = res.get("ergebnis", {})
    total = sum(result.values())
    print(f"★ {total} Lesezeichen eingetragen (Sicherung: {res.get('sicherung')})")
    for path, n in sorted(result.items()):
        print(f"    {path}: +{n}")
    if total < len(tabs_to_save):
        print(f"    ({len(tabs_to_save) - total} waren schon vorhanden)")
    print("    Rückgängig: python3 safari_tabs.py --rueckgaengig")
    return True


def run_undo_last() -> int:
    entry = last_undoable()
    if not entry:
        print("Nichts zum Rückgängigmachen gefunden.")
        return 1
    print(f"Mache rückgängig: {entry.get('aktion')} vom {entry.get('zeit')}")
    for a in entry["hinzugefuegt"]:
        print(f"  – {a['titel'] or a['url']}  ({a['ordner']})")
    if _ask("Wirklich entfernen? [j/N] ") not in ("j", "ja", "y"):
        print("Abgebrochen.")
        return 1
    res = apply_bookmark_change(undo_change_for(entry))
    if not res.get("ok"):
        print(f"⚠️  {res.get('fehler')}")
        return 1
    mark_undone(entry)
    print(f"✓ {len(res.get('entfernt', []))} Lesezeichen entfernt (Sicherung: {res['sicherung']})")
    return 0


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
# Automatik: regelmäßig im Hintergrund aufräumen (macOS launchd)
# --------------------------------------------------------------------------
AUTO_LABEL = "com.safari-tabs.automatik"
AUTO_DEFAULTS: Dict = {
    "haeufigkeit": "monatlich",      # taeglich | woechentlich | monatlich
    "ordnen": True,                  # alles ordnen: lose Lesezeichen in Unterordner, sortieren
    "inaktiv_minuten": 15,           # nur laufen, wenn Mac so lange nicht benutzt wurde
    "schliessen": True,              # eindeutig überflüssige Tabs schließen
    "speichern": True,               # Tabs mit sicherer Ordner-Zuordnung speichern
    "min_score": 10,                 # Mindest-Sicherheit der Zuordnung
    "gespeicherte_schliessen": False,  # gespeicherte Tabs danach schließen
    "benachrichtigen": True,
}
# nur diese Gründe gelten als eindeutig überflüssig
AUTO_SAFE_CLOSE = ("leerer Tab", "Duplikat", "auch am Mac", "auch auf", "Suchergebnis",
                   "Login-", "Fehlerseite", "schon gespeichert", "schon als Lesezeichen")


FREQ_LABEL = {"taeglich": "täglich", "woechentlich": "wöchentlich", "monatlich": "monatlich"}


def _auto_file() -> Path:
    return BRIDGE_DIR / "automatik.json"


def _launch_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{AUTO_LABEL}.plist"


def load_auto_state() -> Dict:
    try:
        st_ = json.loads(_auto_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st_ = {}
    st_["einstellungen"] = {**AUTO_DEFAULTS, **st_.get("einstellungen", {})}
    return st_


def save_auto_state(state: Dict) -> None:
    BRIDGE_DIR.mkdir(exist_ok=True)
    _auto_file().write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def user_idle_seconds() -> float:
    """Sekunden seit der letzten Maus-/Tastatureingabe (macOS)."""
    try:
        out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True,
                             text=True, timeout=5).stdout
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        return int(m.group(1)) / 1e9 if m else 0.0
    except (OSError, subprocess.SubprocessError):
        return 0.0


def auto_due(state: Dict, now: Optional[_dt.datetime] = None) -> bool:
    now = now or _dt.datetime.now()
    last = state.get("letzter_lauf")
    if not last:
        return True
    try:
        last_d = _dt.datetime.fromisoformat(last)
    except ValueError:
        return True
    freq = state["einstellungen"].get("haeufigkeit")
    if freq == "woechentlich":
        return (now - last_d).days >= 7
    if freq == "monatlich":
        return (now.year, now.month) > (last_d.year, last_d.month)
    return now.date() > last_d.date()


def plan_auto(plan: Plan, opts: Dict) -> Tuple[List[Tab], List[Tab], List[Tab]]:
    """(schließen, speichern, zur Prüfung) – nur Eindeutiges wird automatisch erledigt."""
    close = [t for t in plan.by_action(CLOSE) if not t.remote
             and t.reason.startswith(AUTO_SAFE_CLOSE)] if opts.get("schliessen") else []
    save, review = [], []
    for t in plan.by_action(BOOKMARK):
        if (opts.get("speichern") and t.target_path and not t.target_new
                and t.target_score >= opts.get("min_score", 10)):
            save.append(t)
        else:
            review.append(t)
    return close, save, review


def notify(title: str, text: str) -> None:
    if sys.platform != "darwin":
        return
    script = ("function run(argv){ var a = Application.currentApplication(); "
              "a.includeStandardAdditions = true; "
              "a.displayNotification(argv[1], {withTitle: argv[0]}); }")
    subprocess.run(["osascript", "-l", "JavaScript", "-e", script, title, text],
                   capture_output=True)


def _auto_report(close: List[Tab], save: List[Tab], review: List[Tab], result: Dict,
                 organized: Optional[List[Dict]] = None) -> Path:
    d = BRIDGE_DIR / "berichte"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{_dt.datetime.now():%Y-%m-%d_%H%M}.md"
    lines = [f"# Safari-Tabs Automatik – {_dt.datetime.now():%d.%m.%Y %H:%M}", ""]
    if close:
        lines += [f"## Geschlossen ({len(close)})", ""] + \
                 [f"- {t.title or t.url} — {t.reason}" for t in close] + [""]
    if save:
        lines += [f"## Gespeichert ({len(save)})", ""] + \
                 [f"- [{t.title or t.url}]({t.url}) → {t.target_path}" for t in save] + [""]
    if organized:
        lines += ["## Geordnet", ""]
        for r in organized:
            lines.append(f"- **{r['ordner']}**: {len(r['verschoben'])} Lesezeichen in Unterordner"
                         + (" · neu: " + ", ".join(o["titel"][len(r["ordner"]) + 1:]
                                                   for o in r["ordner_neu"]) if r["ordner_neu"] else ""))
        lines += ["", "Alle Ordner sind sortiert (Unterordner alphabetisch, dann Website/Titel).", ""]
    if review:
        lines += [f"## Zur Prüfung – bleiben offen ({len(review)})",
                  "In Claude: „Räum meine Safari-Tabs auf“ ordnet diese mit dir zusammen ein.", ""] + \
                 [f"- [{t.title or t.url}]({t.url})"
                  + (f" — Vorschlag: {t.target_path}" if t.target_path else "") for t in review]
        lines.append("")
    if result.get("sicherung"):
        lines += [f"Sicherung: {result['sicherung']} · Rückgängig: "
                  "`python3 safari_tabs.py --rueckgaengig` oder in Claude „mach das rückgängig“."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_auto(dry_run: bool = False, force: bool = False) -> int:
    """Ein Automatik-Durchlauf (wird von launchd stündlich gestartet)."""
    state = load_auto_state()
    opts = state["einstellungen"]
    stamp = f"[{_dt.datetime.now():%Y-%m-%d %H:%M}]"

    if not state.get("berechtigt") and not dry_run:
        # erster Lauf: Berechtigungen anfragen (macOS zeigt die Dialoge jetzt)
        try:
            read_safari_tabs() if safari_running() else None
            root, _, _ = load_bookmarks_any()
            cleanup_bridge_copies()
        except (SystemExit, BridgeError) as e:
            print(f"{stamp} Berechtigung fehlt: {e}")
            notify("Safari-Tabs Automatik", f"Berechtigung fehlt: {e}")
            return 1
        if not root:
            notify("Safari-Tabs Automatik", "Kein Zugriff auf die Lesezeichen.")
            return 1
        state["berechtigt"] = True
        save_auto_state(state)
        notify("Safari-Tabs Automatik", "Eingerichtet – läuft ab jetzt "
               + FREQ_LABEL.get(opts["haeufigkeit"], opts["haeufigkeit"]) + ".")
        print(f"{stamp} Berechtigungen ok")
        if not force:
            return 0

    if not force and not auto_due(state):
        return 0
    if not safari_running():
        print(f"{stamp} Safari läuft nicht – später erneut")
        return 0
    idle = user_idle_seconds()
    if not force and idle < opts["inaktiv_minuten"] * 60:
        print(f"{stamp} Mac wird gerade benutzt ({int(idle)} s inaktiv) – später erneut")
        return 0

    cfg = load_config(None)
    try:
        root, mode, cloud = load_bookmarks_any()
        tabs, _, _ = read_all_tabs(include_cloud=True, cloud_db=cloud)
    except (SystemExit, BridgeError) as e:
        print(f"{stamp} Fehler: {e}")
        notify("Safari-Tabs Automatik", f"Fehler: {e}")
        return 1
    finally:
        cleanup_bridge_copies()
    if not root:
        notify("Safari-Tabs Automatik", "Kein Zugriff auf die Lesezeichen.")
        return 1
    folders = collect_folders(root)
    plan = analyze(tabs, cfg, bookmark_index(root, cfg["tracking_params"]))
    assign_folders(plan, folders, cfg)
    close, save, review = plan_auto(plan, opts)
    print(f"{stamp} {len(tabs)} Tabs: {len(close)} schließen, {len(save)} speichern, "
          f"{len(review)} zur Prüfung")
    if dry_run:
        for t in close:
            print(f"  ✖ {t.title or t.url}  ({t.reason})")
        for t in save:
            print(f"  ★ {t.title or t.url}  → {t.target_path}")
        for t in review:
            print(f"  ? {t.title or t.url}" + (f"  (Vorschlag {t.target_path})" if t.target_path else ""))
        if opts.get("ordnen"):
            for o in describe_organize(root, cfg):
                print(f"  ▸ {o['ordner']}: neue Unterordner "
                      + ", ".join(p.split('/')[-1] for p in o["neue_unterordner"]))
        return 0

    closed = 0
    if close:
        closed = close_tabs(close)["closed"]
    result: Dict = {}
    if save or opts.get("ordnen"):
        change: Dict = {"add": [_tab_to_dict(t) for t in save],
                        "aktion": "Automatik: " + ("Tabs gespeichert und alles geordnet"
                                                   if opts.get("ordnen") else "Lesezeichen gespeichert")}
        if opts.get("ordnen"):
            change["organize"] = {}
        result = apply_bookmark_change(change)
        if not result.get("ok"):
            print(f"{stamp} Speichern fehlgeschlagen: {result.get('fehler')}")
            notify("Safari-Tabs Automatik", f"Speichern fehlgeschlagen: {result.get('fehler')}")
            save = []
        elif opts.get("gespeicherte_schliessen"):
            keys = {normalize_url(t.url) for t in save if not t.remote}
            closed += close_tabs([c for c in read_safari_tabs()
                                  if normalize_url(c.url) in keys])["closed"]
    organized = [r for r in result.get("umstrukturiert", []) if r.get("ordner_neu") or r.get("verschoben")]
    report = _auto_report(close, save, review, result, organized)
    state["letzter_lauf"] = _dt.datetime.now().isoformat(timespec="seconds")
    state["letztes_ergebnis"] = {"geschlossen": closed, "gespeichert": len(save),
                                 "zur_pruefung": len(review), "bericht": str(report),
                                 "geordnet": sum(len(r["verschoben"]) for r in organized),
                                 "neue_unterordner": sum(len(r["ordner_neu"]) for r in organized)}
    save_auto_state(state)
    moved = state["letztes_ergebnis"]["geordnet"]
    if opts.get("benachrichtigen") and (closed or save or review or moved):
        notify("Safari-Tabs aufgeräumt",
               f"{closed} geschlossen · {len(save)} gespeichert · {moved} einsortiert · "
               f"{len(review)} zur Prüfung")
    print(f"{stamp} fertig: {closed} geschlossen, {len(save)} gespeichert – Bericht {report}")
    return 0


def install_automation(opts: Optional[Dict] = None) -> Dict:
    """Richtet die Automatik ein (launchd, stündliche Prüfung, Arbeit je nach Häufigkeit)."""
    require_macos()
    state = load_auto_state()
    state["einstellungen"].update({k: v for k, v in (opts or {}).items()
                                   if k in AUTO_DEFAULTS and v is not None})
    if state["einstellungen"]["haeufigkeit"] not in ("taeglich", "woechentlich", "monatlich"):
        raise ValueError("haeufigkeit muss taeglich, woechentlich oder monatlich sein")
    state.pop("berechtigt", None)
    save_auto_state(state)
    # stabile Kopie des Programms, unabhängig von Updates/Ort der Erweiterung
    script = BRIDGE_DIR / "safari_tabs.py"
    shutil.copy2(Path(__file__).resolve(), script)
    log = BRIDGE_DIR / "automatik.log"
    plist = {
        "Label": AUTO_LABEL,
        "ProgramArguments": [sys.executable, str(script), "--auto"],
        "StartInterval": 3600,
        "RunAtLoad": False,
        "ProcessType": "Background",
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }
    path = _launch_plist()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        plistlib.dump(plist, fh)
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{AUTO_LABEL}"], capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", domain, str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        r = subprocess.run(["launchctl", "load", "-w", str(path)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"launchctl: {r.stderr.strip()}")
    # erster Lauf sofort: macOS fragt jetzt nach den Berechtigungen
    subprocess.run(["launchctl", "kickstart", f"{domain}/{AUTO_LABEL}"], capture_output=True)
    return {"eingerichtet": True, "einstellungen": state["einstellungen"],
            "plist": str(path), "log": str(log)}


def uninstall_automation() -> Dict:
    path = _launch_plist()
    if sys.platform == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{AUTO_LABEL}"],
                       capture_output=True)
        subprocess.run(["launchctl", "unload", "-w", str(path)], capture_output=True)
    existed = path.exists()
    if existed:
        path.unlink()
    return {"entfernt": existed}


def automation_status() -> Dict:
    state = load_auto_state()
    return {"aktiv": _launch_plist().exists(),
            "berechtigt": state.get("berechtigt", False),
            "einstellungen": state["einstellungen"],
            "letzter_lauf": state.get("letzter_lauf"),
            "letztes_ergebnis": state.get("letztes_ergebnis"),
            "naechster_lauf": "sobald fällig und der Mac "
                              f"{state['einstellungen']['inaktiv_minuten']} Min. nicht benutzt wird"}


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
                    help="Sammelordner für Tabs ohne passenden Ordner (Standard: keiner)")
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
    ap.add_argument("--rueckgaengig", action="store_true",
                    help="letzte Speicherung rückgängig machen (nur deren Lesezeichen)")
    ap.add_argument("--sicherungen", action="store_true",
                    help="vorhandene Sicherungen der Lesezeichen auflisten")
    ap.add_argument("--wiederherstellen", metavar="NAME",
                    help="Sicherung zurückspielen (Name aus --sicherungen)")
    ap.add_argument("--sortieren", metavar="ORDNER",
                    help="Ordner sortieren (Unterordner alphabetisch zuerst, dann nach Website/Titel)")
    ap.add_argument("--auto", action="store_true",
                    help="Automatik-Durchlauf (normalerweise von launchd gestartet)")
    ap.add_argument("--erzwingen", action="store_true",
                    help="mit --auto: sofort ausführen, auch wenn nicht fällig/Mac benutzt")
    ap.add_argument("--auto-installieren", action="store_true",
                    help="Automatik einrichten (läuft im Hintergrund)")
    ap.add_argument("--auto-entfernen", action="store_true", help="Automatik ausschalten")
    ap.add_argument("--auto-status", action="store_true", help="Status der Automatik")
    ap.add_argument("--haeufigkeit", choices=["taeglich", "woechentlich", "monatlich"],
                    help="mit --auto-installieren")
    ap.add_argument("--inaktiv-minuten", type=int, help="mit --auto-installieren")
    ap.add_argument("--gespeicherte-schliessen", action="store_true",
                    help="mit --auto-installieren: gespeicherte Tabs auch schließen")
    ap.add_argument("--bridge-op", help=argparse.SUPPRESS)
    ap.add_argument("--bridge-token", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.bridge_op:
        return bridge_main(args.bridge_op, args.bridge_token or "x")
    if args.auto:
        return run_auto(dry_run=args.overview, force=args.erzwingen)
    if args.auto_installieren:
        res = install_automation({"haeufigkeit": args.haeufigkeit,
                                  "inaktiv_minuten": args.inaktiv_minuten,
                                  "gespeicherte_schliessen": args.gespeicherte_schliessen or None})
        e = res["einstellungen"]
        print(f"✓ Automatik eingerichtet ({FREQ_LABEL[e['haeufigkeit']]}, "
              f"wenn der Mac {e['inaktiv_minuten']} Min. nicht benutzt wird).\n"
              f"  Protokoll: {res['log']}\n  Bitte die macOS-Abfragen (Safari steuern) erlauben.")
        return 0
    if args.auto_entfernen:
        print("✓ Automatik ausgeschaltet" if uninstall_automation()["entfernt"]
              else "Automatik war nicht eingerichtet")
        return 0
    if args.auto_status:
        print(json.dumps(automation_status(), ensure_ascii=False, indent=2))
        return 0
    if args.rueckgaengig:
        require_macos()
        return run_undo_last()
    if args.sortieren:
        require_macos()
        root, _, _ = load_bookmarks_any()
        cleanup_bridge_copies()
        f = find_folder(args.sortieren, collect_folders(root)) if root else None
        if not f:
            print(f"Ordner „{args.sortieren}“ nicht gefunden.")
            return 1
        res = apply_bookmark_change({"sort": [f.path]})
        print(f"✓ „{f.path}“ sortiert (Sicherung: {res['sicherung']})" if res.get("ok")
              else f"⚠️  {res.get('fehler')}")
        return 0 if res.get("ok") else 1
    if args.sicherungen:
        for b in list_backups():
            print(f"  {b['name']}   {b['zeit']}   {b['groesse_kb']} KB")
        return 0
    if args.wiederherstellen:
        require_macos()
        if _ask(f"Lesezeichen auf {args.wiederherstellen} zurücksetzen? [j/N] ") not in ("j", "ja"):
            return 1
        res = apply_bookmark_change({"restore": args.wiederherstellen})
        print(("✓ zurückgespielt, vorheriger Stand gesichert als " + res["sicherung"])
              if res.get("ok") else f"⚠️  {res.get('fehler')}")
        return 0 if res.get("ok") else 1

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
    if folders:
        unassigned = [t for t in to_save if not t.target_path]
        if unassigned:
            print(f"ℹ️  {len(unassigned)} Tabs ohne Ordner werden nicht gespeichert "
                  f"(Nr. {', '.join(str(t.num) for t in unassigned)}) – mit z. B. '4>Video' "
                  "zuordnen.")
            to_save = [t for t in to_save if t.target_path]
        problems = check_new_folders(to_save)
        if problems:
            print("⚠️  Nicht gespeichert:\n   " + "\n   ".join(problems))
            return 1

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
