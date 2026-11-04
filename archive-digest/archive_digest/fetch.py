"""Snapshots von archive.ph (bzw. archive.today & Co.) abrufen."""

from __future__ import annotations

from urllib.parse import urlparse

import requests

ARCHIVE_HOSTS = {
    "archive.ph",
    "archive.today",
    "archive.is",
    "archive.li",
    "archive.vn",
    "archive.md",
    "archive.fo",
}

DEFAULT_MIRROR = "https://archive.ph"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


class FetchError(RuntimeError):
    """Snapshot konnte nicht geladen werden."""


def is_archive_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.") in ARCHIVE_HOSTS


def snapshot_url(url: str, mirror: str = DEFAULT_MIRROR) -> str:
    """Archiv-Link direkt verwenden, sonst den neuesten Snapshot der Original-URL."""
    url = url.strip()
    if not urlparse(url).scheme:
        url = "https://" + url
    if is_archive_url(url):
        return url
    return f"{mirror.rstrip('/')}/newest/{url}"


def looks_like_captcha(html: str) -> bool:
    lowered = html.lower()
    return "g-recaptcha" in lowered or "h-captcha" in lowered or (
        "one more step" in lowered and "captcha" in lowered
    )


def fetch_snapshot(url: str, mirror: str = DEFAULT_MIRROR, timeout: float = 30.0) -> tuple[str, str]:
    """Gibt (finale URL, HTML) des Snapshots zurück."""
    target = snapshot_url(url, mirror)
    try:
        resp = requests.get(target, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise FetchError(f"archive.ph nicht erreichbar: {exc}") from exc

    if resp.status_code == 404:
        raise FetchError(
            "Kein Snapshot gefunden. Seite zuerst archivieren: "
            f"{mirror.rstrip('/')}/?url={url}"
        )
    if resp.status_code == 429:
        raise FetchError("archive.ph drosselt gerade (HTTP 429). Später erneut versuchen.")
    if resp.status_code >= 400:
        raise FetchError(f"archive.ph antwortete mit HTTP {resp.status_code}.")

    resp.encoding = resp.encoding or resp.apparent_encoding
    html = resp.text
    if looks_like_captcha(html):
        raise FetchError(
            "archive.ph verlangt ein CAPTCHA. Öffne den Link im Browser, speichere die Seite "
            "(Strg+S, 'nur HTML') und nutze: archive-digest --html datei.html"
        )
    return resp.url, html
