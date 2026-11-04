"""Artikeltext aus einer archive.ph-Snapshot-Seite herausholen."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

NOISE_TAGS = [
    "script", "style", "noscript", "svg", "iframe", "form", "button",
    "nav", "footer", "aside", "input", "select", "textarea",
]
BLOCK_TAGS = ["h1", "h2", "h3", "h4", "p", "li", "blockquote", "figcaption"]
MIN_BLOCK_CHARS = 25


@dataclass
class Article:
    title: str
    text: str
    original_url: str | None = None
    archived_at: str | None = None
    snapshot_url: str | None = None
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_original_url(soup: BeautifulSoup) -> str | None:
    # archive.ph zeigt die Original-URL im Kopfbereich als Suchfeld bzw. Link an.
    field_ = soup.find("input", attrs={"name": "q"})
    if isinstance(field_, Tag) and field_.get("value", "").startswith("http"):
        return field_["value"]
    for meta_name in ("og:url", "twitter:url"):
        tag = soup.find("meta", attrs={"property": meta_name}) or soup.find("meta", attrs={"name": meta_name})
        if isinstance(tag, Tag):
            content = tag.get("content", "")
            if content.startswith("http") and "archive." not in content:
                return content
    return None


def _find_archived_at(soup: BeautifulSoup) -> str | None:
    tag = soup.find("time", attrs={"itemprop": "pubdate"}) or soup.find("time")
    if isinstance(tag, Tag):
        return tag.get("datetime") or _clean(tag.get_text())
    return None


def _content_root(soup: BeautifulSoup) -> Tag:
    for selector in ("#CONTENT", "article", "main", "[role=main]", "body"):
        node = soup.select_one(selector)
        if node is not None:
            return node
    return soup


def _title(soup: BeautifulSoup, root: Tag) -> str:
    h1 = root.find("h1")
    if isinstance(h1, Tag) and _clean(h1.get_text()):
        return _clean(h1.get_text())
    og = soup.find("meta", attrs={"property": "og:title"})
    if isinstance(og, Tag) and og.get("content"):
        return _clean(og["content"])
    if soup.title and soup.title.string:
        return _clean(soup.title.string)
    return "(ohne Titel)"


def _blocks(root: Tag) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for node in root.find_all(BLOCK_TAGS):
        # Verschachtelte Blöcke (z.B. <p> in <li>) nur einmal zählen.
        if node.find_parent(BLOCK_TAGS) is not None:
            continue
        text = _clean(node.get_text(" "))
        is_heading = node.name in {"h1", "h2", "h3", "h4"}
        if not text or text in seen or (len(text) < MIN_BLOCK_CHARS and not is_heading):
            continue
        seen.add(text)
        lines.append(f"## {text}" if is_heading else text)
    return lines


def extract_article(html: str, snapshot_url: str | None = None) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    original_url = _find_original_url(soup)
    archived_at = _find_archived_at(soup)

    root = _content_root(soup)
    for tag in root.find_all(NOISE_TAGS):
        tag.decompose()

    title = _title(soup, root)
    lines = _blocks(root)
    text = "\n\n".join(lines)

    # Fallback, falls archive.ph die Struktur zu <div>s plattgedrückt hat.
    if len(text) < 500:
        raw = [_clean(line) for line in root.get_text("\n").splitlines()]
        text = "\n".join(line for line in raw if len(line) >= MIN_BLOCK_CHARS)

    meta = {}
    for name in ("author", "description", "article:published_time"):
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if isinstance(tag, Tag) and tag.get("content"):
            meta[name] = _clean(tag["content"])

    return Article(
        title=title,
        text=text,
        original_url=original_url,
        archived_at=archived_at,
        snapshot_url=snapshot_url,
        meta=meta,
    )
