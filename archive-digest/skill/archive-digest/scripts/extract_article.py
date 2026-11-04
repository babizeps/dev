#!/usr/bin/env python3
"""Artikeltext aus einer gespeicherten archive.ph-Seite herausholen.

Aufruf: python extract_article.py seite.html
Gibt Titel, Original-URL, Archivdatum, Wortzahl und den Artikeltext aus.
Benötigt nur die Standardbibliothek.
"""

import re
import sys
from html.parser import HTMLParser

BLOCKS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote", "figcaption"}
SKIP = {"script", "style", "noscript", "svg", "iframe", "form", "button",
        "nav", "footer", "aside", "select", "textarea", "head"}
VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}
MIN_CHARS = 25


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # offene Tags
        self.skip_depth = 0
        self.in_content = False
        self.content_depth = None
        self.block = None        # (tag, [text])
        self.blocks = []
        self.all_text = []
        self.title = ""
        self.in_title = False
        self.original_url = None
        self.archived_at = None
        self.in_time = False
        self.og_title = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("name") == "q" and (a.get("value") or "").startswith("http"):
            self.original_url = self.original_url or a["value"]
        if tag == "meta" and a.get("property") == "og:title":
            self.og_title = a.get("content")
        if tag == "time" and not self.archived_at:
            self.archived_at = a.get("datetime")
            self.in_time = not self.archived_at
        if tag == "title":
            self.in_title = True
        if tag in VOID:
            return
        self.stack.append(tag)
        if a.get("id") == "CONTENT" and not self.in_content:
            self.in_content, self.content_depth = True, len(self.stack)
        if tag in SKIP:
            self.skip_depth += 1
        if tag in BLOCKS and self.block is None and not self.skip_depth:
            self.block = (tag, [], len(self.stack))

    def handle_endtag(self, tag):
        if tag in VOID or tag not in self.stack:
            return
        while self.stack:
            open_tag = self.stack.pop()
            depth = len(self.stack) + 1
            if open_tag in SKIP:
                self.skip_depth -= 1
            if self.block and self.block[2] == depth:
                self.blocks.append((self.block[0], clean("".join(self.block[1])), self.in_content))
                self.block = None
            if self.in_content and depth == self.content_depth:
                self.in_content = False
            if open_tag == tag:
                break
        if tag == "title":
            self.in_title = False
        if tag == "time":
            self.in_time = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_time:
            self.archived_at = clean(data) or self.archived_at
        if self.skip_depth:
            return
        if self.block:
            self.block[1].append(data)
        self.all_text.append((data, self.in_content))


def extract(html):
    p = Extractor()
    p.feed(html)
    has_content = any(in_c for _, _, in_c in p.blocks)
    lines, seen = [], set()
    title = None
    for tag, text, in_c in p.blocks:
        if has_content and not in_c:
            continue
        heading = tag.startswith("h")
        if not text or text in seen or (len(text) < MIN_CHARS and not heading):
            continue
        seen.add(text)
        if tag == "h1" and title is None:
            title = text
        lines.append(f"## {text}" if heading else text)
    body = "\n\n".join(lines)
    if len(body) < 500:  # Fallback, falls archive.ph alles zu <div>s gemacht hat
        raw = "".join(t for t, in_c in p.all_text if in_c or not has_content)
        body = "\n".join(l for l in (clean(x) for x in raw.splitlines()) if len(l) >= MIN_CHARS)
    title = title or p.og_title or clean(p.title) or "(ohne Titel)"
    return {
        "title": title,
        "original_url": p.original_url,
        "archived_at": p.archived_at,
        "words": len(body.split()),
        "text": body,
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python extract_article.py seite.html")
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        html = f.read()
    if "g-recaptcha" in html or "h-captcha" in html:
        print("WARNUNG: Die Datei ist eine CAPTCHA-Seite, kein Artikel.", file=sys.stderr)
    art = extract(html)
    print(f"Titel: {art['title']}")
    print(f"Original-URL: {art['original_url'] or 'unbekannt'}")
    print(f"Archiviert: {art['archived_at'] or 'unbekannt'}")
    print(f"Wörter: {art['words']}")
    print()
    print(art["text"])


if __name__ == "__main__":
    main()
