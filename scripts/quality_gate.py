#!/usr/bin/env python3
"""Interpretive Governance - Q-Layer quality gate.

This gate is intentionally strict: it treats public doctrine as a versioned interface.

Fail-fast rules prevent:
- accidental operability
- semantic drift (duplicate metadata)
- discovery regressions (missing sitemap/manifest coverage)
"""

import sys
import json
import re
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://interpretive-governance.org"

SITEMAP = ROOT / "sitemap.xml"
MANIFEST = ROOT / "ig-manifest.json"
TERMS = ROOT / "data" / "terms.json"
DOCS = ROOT / "data" / "documents.json"

CLASSIFICATIONS = {"normative", "informative"}

LANG_EN = "en"
LANG_FR = "fr-CA"

def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def canonical_from_rel(rel: Path) -> str:
    rel_s = rel.as_posix()

    # Any */index.html is a clean directory URL.
    if rel_s.endswith("index.html"):
        prefix = rel_s[: -len("index.html")]  # "" or "en/" or "fr/"
        return SITE.rstrip("/") + "/" + prefix

    if rel_s.endswith(".html"):
        rel_s = rel_s[:-5]
    return SITE + "/" + rel_s

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

def read_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing required JSON file: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {e}")

def file_for_url(url_path: str) -> Path:
    """Map a canonical URL path to a repository HTML file."""
    if not url_path.startswith("/"):
        url_path = "/" + url_path

    if url_path == "/":
        return ROOT / "index.html"

    if url_path.endswith("/"):
        rel = url_path.strip("/") + "/index.html"
        return ROOT / rel

    rel = url_path.lstrip("/") + ".html"
    return ROOT / rel

def is_term_page(rel: Path) -> bool:
    s = rel.as_posix()
    return "/terms/" in s or "/termes/" in s

def main() -> None:
    # ---- Machine surface checks (registries + manifest) ----
    terms = read_json(TERMS)
    docs = read_json(DOCS)
    manifest = read_json(MANIFEST)

    for obj, name in [(terms, "terms registry"), (docs, "documents registry")]:
        for k in ["schemaVersion", "doctrineVersion", "generatedAt", "site"]:
            if k not in obj:
                fail(f"{name} missing key: {k}")
        if obj.get("site") != SITE:
            warn(f"{name} site != {SITE}")

    doctrine_version = terms.get("doctrineVersion")
    if docs.get("doctrineVersion") != doctrine_version:
        fail("documents registry doctrineVersion != terms registry doctrineVersion")

    if manifest.get("version") != doctrine_version:
        warn("manifest version != doctrineVersion (still acceptable, but should be aligned)")

    # Manifest must reference the two canonical registries
    dist = manifest.get("distribution", [])
    dist_urls = {d.get("contentUrl") for d in dist if isinstance(d, dict)}
    if f"{SITE}/data/terms.json" not in dist_urls:
        fail("manifest missing /data/terms.json distribution entry")
    if f"{SITE}/data/documents.json" not in dist_urls:
        fail("manifest missing /data/documents.json distribution entry")

    ok("Machine surface JSON checks passed")

    # ---- HTML checks (all indexable pages) ----
    html_files = sorted(
        [
            p for p in ROOT.rglob("*.html")
            if p.name != "404.html"
            and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
        ],
        key=lambda p: p.as_posix()
    )

    if not html_files:
        fail("no HTML files found")

    titles: list[tuple[str, str]] = []
    descriptions: list[tuple[str, str]] = []
    internal_html_links: list[tuple[str, str]] = []

    for p in html_files:
        rel = p.relative_to(ROOT)
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")

        # lang
        if not soup.html or not soup.html.get("lang"):
            fail(f"{rel}: missing <html lang>")

        # title
        if not soup.title or not soup.title.get_text(strip=True):
            fail(f"{rel}: missing <title>")
        titles.append((rel.as_posix(), soup.title.get_text(strip=True)))

        # description
        desc = parse_meta(soup, "description", "name")
        if not desc:
            fail(f"{rel}: missing meta description")
        descriptions.append((rel.as_posix(), desc))

        # canonical
        can = parse_link(soup, "canonical")
        if not can:
            fail(f"{rel}: missing canonical link")
        if ".html" in can:
            fail(f"{rel}: canonical contains .html ({can})")
        expected_can = canonical_from_rel(rel)
        if can != expected_can:
            warn(f"{rel}: canonical mismatch (found {can}, expected {expected_can})")
        if not can.startswith(SITE):
            warn(f"{rel}: canonical not on {SITE} ({can})")

        # JSON-LD
        if not soup.find("script", attrs={"type": "application/ld+json"}):
            fail(f"{rel}: missing JSON-LD structured data")

        # JSON-LD content sanity: this site publishes pages (doctrine), not articles.
        try:
            ld_raw = soup.find("script", attrs={"type": "application/ld+json"}).string or ""
            ld = json.loads(ld_raw.strip() or "{}")
        except Exception as e:
            fail(f"{rel}: invalid JSON-LD (cannot parse): {e}")

        graph = []
        if isinstance(ld, dict):
            graph = ld.get("@graph", []) if isinstance(ld.get("@graph", []), list) else []

        for node in graph:
            if not isinstance(node, dict):
                continue
            if "additionalProperty" in node:
                fail(f"{rel}: JSON-LD must not use additionalProperty (validator incompatibility)")
            t = node.get("@type")
            types = t if isinstance(t, list) else ([t] if t else [])
            if "Article" in types:
                fail(f"{rel}: JSON-LD must not declare Article; use WebPage/ProfilePage/etc.")

        # IG meta
        classification = parse_meta(soup, "ig:classification", "name")
        if not classification or classification not in CLASSIFICATIONS:
            fail(f"{rel}: missing/invalid ig:classification (expected {sorted(CLASSIFICATIONS)})")
        status = parse_meta(soup, "ig:status", "name")
        if status != "doctrinal":
            fail(f"{rel}: ig:status must be 'doctrinal'")
        operability = parse_meta(soup, "ig:operability", "name")
        if operability != "non-operational":
            fail(f"{rel}: ig:operability must be 'non-operational'")
        dv = parse_meta(soup, "ig:doctrine-version", "name")
        if dv != doctrine_version:
            fail(f"{rel}: ig:doctrine-version mismatch (found {dv}, expected {doctrine_version})")

        if is_term_page(rel):
            entity_id = parse_meta(soup, "ig:entity-id", "name")
            term_code = parse_meta(soup, "ig:termCode", "name")
            entity_type = parse_meta(soup, "ig:entity-type", "name")
            if not entity_id or not term_code:
                fail(f"{rel}: term page missing ig:entity-id or ig:termCode")
            if entity_type != "DefinedTerm":
                fail(f"{rel}: term page ig:entity-type must be 'DefinedTerm'")
        else:
            doc_id = parse_meta(soup, "ig:doc-id", "name")
            if not doc_id:
                fail(f"{rel}: document page missing ig:doc-id")

        # internal links (.html)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            if ".html" in href:
                internal_html_links.append((rel.as_posix(), href))

    # Uniqueness checks
    title_counts = Counter(t for _, t in titles)
    dup_titles = [t for t, c in title_counts.items() if c > 1]
    if dup_titles:
        fail(f"duplicate titles detected: {dup_titles[:10]}")

    desc_counts = Counter(d for _, d in descriptions)
    dup_desc = [d for d, c in desc_counts.items() if c > 1]
    if dup_desc:
        fail("duplicate meta descriptions detected")

    if internal_html_links:
        fail(f"internal .html links detected (example: {internal_html_links[0]})")

    ok("HTML checks passed")

    # ---- Registry consistency checks ----
    # Documents registry: each variant URL must exist as an HTML file
    for doc in docs.get("documents", []):
        variants = doc.get("variants", {})
        if not isinstance(variants, dict) or not variants:
            fail(f"documents registry: doc {doc.get('id')} missing variants")
        for lang, v in variants.items():
            url_path = v.get("url")
            if not url_path:
                fail(f"documents registry: doc {doc.get('id')} variant {lang} missing url")
            target = file_for_url(url_path)
            if not target.exists():
                fail(f"documents registry: missing HTML file for {url_path} -> {target.relative_to(ROOT)}")

    # Terms registry: ensure pages exist for every term (en/fr-CA)
    for t in terms.get("terms", []):
        slug = t.get("slug")
        tid = t.get("id")
        if not slug or not tid:
            fail("terms registry: term missing id or slug")
        for prefix in ["/en/terms/", "/fr/termes/"]:
            url_path = prefix + slug
            target = file_for_url(url_path)
            if not target.exists():
                fail(f"terms registry: missing term page {url_path} -> {target.relative_to(ROOT)}")

    ok("Registry-to-files consistency passed")

    # ---- Sitemap checks ----
    if not SITEMAP.exists():
        fail("missing sitemap.xml")

    sitemap_text = SITEMAP.read_text(encoding="utf-8")
    if ".html" in sitemap_text:
        fail("sitemap.xml contains .html URLs")

    expected = {canonical_from_rel(p.relative_to(ROOT)) for p in html_files}
    found = set(re.findall(r"<loc>(.*?)</loc>", sitemap_text))
    missing = sorted(expected - found)
    if missing:
        fail(f"sitemap.xml missing {len(missing)} URL(s): {missing[:10]}")

    ok("Sitemap checks passed")
    print("All quality gates passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
