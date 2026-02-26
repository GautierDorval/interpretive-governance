#!/usr/bin/env python3

import sys
from pathlib import Path
from collections import defaultdict, Counter
from bs4 import BeautifulSoup
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://interpretive-governance.org"

HTML_FILES = sorted([p for p in ROOT.glob("*.html") if p.name != "404.html"])
SITEMAP = ROOT / "sitemap.xml"

def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def canonical_from_file(name: str) -> str:
    # Cloudflare Pages "clean URLs": /foo.html => /foo
    if name == "index.html":
        return SITE + "/"
    return SITE + "/" + name.replace(".html","")

def parse_meta(soup: BeautifulSoup, key: str, attr: str = "name") -> str | None:
    tag = soup.find("meta", attrs={attr: key})
    return tag.get("content") if tag else None

def parse_link(soup: BeautifulSoup, rel: str, hreflang: str | None = None) -> str | None:
    for link in soup.find_all("link", rel=True):
        rel_val = link.get("rel")
        if isinstance(rel_val, list):
            rel_val = rel_val[0] if rel_val else None
        if rel_val != rel:
            continue
        if hreflang is not None and link.get("hreflang") != hreflang:
            continue
        if hreflang is None and link.get("hreflang") is not None and rel == "canonical":
            continue
        return link.get("href")
    return None

def main() -> None:
    titles = []
    descriptions = []
    canonicals = []
    internal_html_links = []

    for p in HTML_FILES:
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")

        # lang
        if not soup.html or not soup.html.get("lang"):
            fail(f"{p.name}: missing <html lang>")
        # title
        if not soup.title or not soup.title.get_text(strip=True):
            fail(f"{p.name}: missing <title>")
        titles.append((p.name, soup.title.get_text(strip=True)))

        # description
        desc = parse_meta(soup, "description", "name")
        if not desc:
            fail(f"{p.name}: missing meta description")
        descriptions.append((p.name, desc))

        # canonical
        can = parse_link(soup, "canonical")
        if not can:
            fail(f"{p.name}: missing canonical link")
        if ".html" in can:
            fail(f"{p.name}: canonical contains .html ({can})")
        if not can.startswith(SITE):
            warn(f"{p.name}: canonical not on {SITE} ({can})")
        canonicals.append((p.name, can))

        # JSON-LD
        if not soup.find("script", attrs={"type":"application/ld+json"}):
            fail(f"{p.name}: missing JSON-LD structured data")

        # internal links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            if ".html" in href:
                internal_html_links.append((p.name, href))

    # Uniqueness checks
    title_counts = Counter(t for _,t in titles)
    dup_titles = [t for t,c in title_counts.items() if c > 1]
    if dup_titles:
        fail(f"duplicate titles detected: {dup_titles}")

    desc_counts = Counter(d for _,d in descriptions)
    dup_desc = [d for d,c in desc_counts.items() if c > 1]
    if dup_desc:
        fail("duplicate meta descriptions detected")

    if internal_html_links:
        fail(f"internal .html links detected (example: {internal_html_links[0]})")

    ok("HTML checks passed")

    # Sitemap checks
    if not SITEMAP.exists():
        fail("missing sitemap.xml")

    sitemap_text = SITEMAP.read_text(encoding="utf-8")
    if ".html" in sitemap_text:
        fail("sitemap.xml contains .html URLs")

    # Ensure every indexable HTML file is in sitemap
    expected = {canonical_from_file(p.name) for p in HTML_FILES}
    found = set(re.findall(r"<loc>(.*?)</loc>", sitemap_text))
    missing = sorted(expected - found)
    if missing:
        fail(f"sitemap.xml missing {len(missing)} URL(s): {missing[:5]}")

    ok("Sitemap checks passed")
    print("All quality gates passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
