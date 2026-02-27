#!/usr/bin/env python3
"""
Build deterministic machine-first artifacts from canonical registries.

Source of truth:
- data/terms.json
- data/documents.json

Outputs (generated, deterministic):
- ig-manifest.json (+ /.well-known mirror)
- sitemap.xml
- /en/glossary.html and /fr/glossaire.html
- /en/terms/* and /fr/termes/* pages (+ JSON-LD)
- /.well-known mirrors of registries
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from html import escape
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://interpretive-governance.org"

TERMS_PATH = ROOT / "data" / "terms.json"
DOCS_PATH = ROOT / "data" / "documents.json"

LANG_EN = "en"
LANG_FR = "fr-CA"
LANG_XDEFAULT = "x-default"

ASSET_VERSION = "20260227-1"  # bump when assets change

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def truncate(s: str, max_len: int = 175) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    cut = s[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"

def og_locale_for(lang: str) -> str:
    return "fr_CA" if lang.startswith("fr") else "en_US"

def jsonld_website_person() -> list[dict]:
    return [
        {
            "@type": "WebSite",
            "@id": f"{SITE}/#website",
            "url": f"{SITE}/",
            "name": "Interpretive Governance",
            "description": "Doctrinal reference for bounded interpretation and auditable machine responses (non-operational).",
            "inLanguage": [LANG_EN, LANG_FR],
            "publisher": {"@id": f"{SITE}/#person"},
        },
        {
            "@type": "Person",
            "@id": f"{SITE}/#person",
            "name": "Gautier Dorval",
            "url": "https://gautierdorval.com/",
            "sameAs": [
                "https://gautierdorval.com/",
                "https://github.com/GautierDorval/gautierdorval-identity",
            ],
        },
    ]

def jsonld_webpage(
    canonical: str,
    name: str,
    description: str,
    lang: str,
    classification: str,
    doctrine_version: str,
    doc_id: str | None = None,
    entity_id: str | None = None,
    page_type: str = "WebPage",
) -> dict:
    """Schema.org for doctrinal pages (not articles).

    Governance metadata lives in:
    - IG meta tags (ig:* in HTML head)
    - registries (data/terms.json, data/documents.json)
    - canonical manifest (ig-manifest.json)

    Embedded JSON-LD is intentionally minimal and strictly Schema.org.
    """
    ids: list[str] = []
    if doc_id:
        ids.append(doc_id)
    if entity_id and entity_id not in ids:
        ids.append(entity_id)

    page: dict = {
        "@type": page_type,
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": name,
        "description": description,
        "isPartOf": {"@id": f"{SITE}/#website"},
        "inLanguage": lang,
        "dateModified": read_json(TERMS_PATH).get("generatedAt"),
        "author": {"@id": f"{SITE}/#person"},
        "about": {"@type": "Thing", "name": "Interpretive Governance"},
        "keywords": [classification, "doctrinal", "non-operational", f"doctrine:{doctrine_version}"],
    }

    if ids:
        page["identifier"] = ids[0] if len(ids) == 1 else ids

    return page

def jsonld_defined_term(term: dict, lang: str, canonical: str, termset_id: str) -> dict:
    v = term["variants"][lang]
    return {
        "@type": "DefinedTerm",
        "@id": f"{canonical}#term",
        "url": canonical,
        "name": v["label"],
        "description": v["definition"],
        "inLanguage": lang,
        "termCode": term["termCode"],
        "identifier": term["id"],
        "inDefinedTermSet": {"@id": termset_id},
    }

def hreflang_cluster(en_url: str, fr_url: str, x_default_url: str | None = None) -> dict[str, str]:
    alts = {
        LANG_EN: en_url,
        LANG_FR: fr_url,
    }
    alts[LANG_XDEFAULT] = x_default_url or f"{SITE}/"
    return alts

def make_head_common(
    title: str,
    description: str,
    canonical: str,
    lang: str,
    hreflang_alt: dict[str, str],
    doctrine_version: str,
    og_type: str = "website",
) -> str:
    hreflang_links = "\n".join(
        [f'<link rel="alternate" hreflang="{hl}" href="{url}"/>' for hl, url in hreflang_alt.items()]
    )
    return f"""<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}"/>
<meta name="robots" content="index,follow"/>
<meta name="ig:status" content="doctrinal"/>
<meta name="ig:operability" content="non-operational"/>
<meta name="ig:doctrine-version" content="{doctrine_version}"/>
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v={ASSET_VERSION}"/>
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VERSION}"/>
<link rel="canonical" href="{canonical}"/>
{hreflang_links}
<link rel="alternate" type="application/ld+json" href="{SITE}/ig-manifest.json" title="Interpretive Governance canonical manifest"/>
<link rel="alternate" type="application/json" href="{SITE}/data/terms.json" title="Interpretive Governance terms registry"/>
<meta property="og:site_name" content="Interpretive Governance"/>
<meta property="og:title" content="{escape(title)}"/>
<meta property="og:description" content="{escape(description)}"/>
<meta property="og:type" content="{og_type}"/>
<meta property="og:url" content="{canonical}"/>
<meta property="og:image" content="{SITE}/assets/og.png"/>
<meta property="og:locale" content="{og_locale_for(lang)}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{escape(title)}"/>
<meta name="twitter:description" content="{escape(description)}"/>
<meta name="twitter:image" content="{SITE}/assets/og.png"/>"""

def make_topbar_nav(lang: str, active: str, lang_switch_href: str, lang_switch_label: str) -> str:
    is_en = lang == LANG_EN
    if is_en:
        items = [
            ("home", "Home", "/en/"),
            ("principles", "Principles", "/en/principles"),
            ("architecture", "Architecture", "/en/architecture"),
            ("scope", "Scope", "/en/scope"),
            ("glossary", "Glossary", "/en/glossary"),
            ("author", "Author &amp; governance", "/en/author"),
            ("notes", "Notes", "/en/notes"),
        ]
    else:
        items = [
            ("home", "Accueil", "/fr/"),
            ("principles", "Principes", "/fr/principes"),
            ("architecture", "Architecture", "/fr/architecture"),
            ("scope", "Portée", "/fr/portee"),
            ("glossary", "Glossaire", "/fr/glossaire"),
            ("author", "Auteur &amp; gouvernance", "/fr/auteur"),
            ("notes", "Notes", "/fr/notes"),
        ]

    links = []
    for key, label, href in items:
        cls = "active" if key == active else ""
        links.append(f'<a class="{cls}" href="{href}">{label}</a>')
    links.append(f'<a href="{lang_switch_href}">{lang_switch_label}</a>')
    return "\n".join(links)

def make_term_page(term: dict, lang: str, doctrine_version: str, last_updated: str, term_by_id: dict[str, dict]) -> str:
    is_en = lang == LANG_EN
    label = term["variants"][lang]["label"]
    definition = term["variants"][lang]["definition"]
    prefix = "/en/terms/" if is_en else "/fr/termes/"
    other_prefix = "/fr/termes/" if is_en else "/en/terms/"
    canonical = SITE + prefix + term["slug"]
    title = f"{label} | {'Glossary' if is_en else 'Glossaire'} | Interpretive Governance"
    description = truncate(definition)

    hreflang_alt = hreflang_cluster(
        SITE + "/en/terms/" + term["slug"],
        SITE + "/fr/termes/" + term["slug"],
        SITE + "/",
    )
    head_common = make_head_common(title, description, canonical, lang, hreflang_alt, doctrine_version)

    entity_meta = f"""
<meta name="ig:classification" content="normative"/>
<meta name="ig:entity-type" content="DefinedTerm"/>
<meta name="ig:entity-id" content="{term['id']}"/>
<meta name="ig:termCode" content="{term['termCode']}"/>
<meta name="ig:entity-status" content="{term['status']}"/>""".strip()

    termset_id = f"{SITE}/en/glossary#definedtermset" if is_en else f"{SITE}/fr/glossaire#definedtermset"
    graph = jsonld_website_person() + [
        jsonld_webpage(canonical, label, description, lang, "normative", doctrine_version, entity_id=term["id"]),
        jsonld_defined_term(term, lang, canonical, termset_id),
    ]
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

    related_ids = term.get("related", [])
    related_links = []
    for rid in related_ids:
        rt = term_by_id.get(rid)
        if not rt:
            continue
        rl = rt["variants"][lang]["label"]
        related_links.append(f'<li><a href="{prefix}{rt["slug"]}">{escape(rl)}</a></li>')
    related_html = ""
    if related_links:
        related_html = f"""
<h2>{'Related terms' if is_en else 'Termes liés'}</h2>
<div class="card">
<ul>
{chr(10).join(related_links)}
</ul>
</div>"""

    nav = make_topbar_nav(lang, "glossary", other_prefix + term["slug"], "Français" if is_en else "English")
    badge_label = "normative" if is_en else "normatif"

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
{head_common}
{entity_meta}
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
<header class="topbar">
  <div class="container">
    <div class="brand">
      <img src="/assets/logo.svg?v={ASSET_VERSION}" width="34" height="34" alt="Interpretive Governance"/>
      <div>
        <div><strong>Interpretive Governance</strong> <span class="badge">doctrinal</span></div>
        <div class="muted" style="font-size:13px">{'Personal conceptual reference. Not an implementation.' if is_en else 'Référence conceptuelle personnelle. Non opérable.'}</div>
      </div>
    </div>
    <nav>
{nav}
    </nav>
  </div>
</header>
<main class="container">
  <h1>{escape(label)}</h1>
  <div class="docmeta">
    <span class="badge badge--normative">{badge_label}</span>
    <span class="muted">{'Entity' if is_en else 'Entité'}: <code>{term['id']}</code> · {'Doctrine' if is_en else 'Doctrine'} {doctrine_version} · {'Non-operational' if is_en else 'Non opérable'}</span>
  </div>

  <div class="card">
    <p><strong>{'Definition' if is_en else 'Définition'}</strong></p>
    <p>{escape(definition)}</p>
  </div>

  <div class="card">
    <div class="kv"><div>{'Term code' if is_en else 'Code terme'}</div><div><code>{term['termCode']}</code></div></div>
    <div class="kv"><div>{'Entity status' if is_en else 'Statut entité'}</div><div><code>{escape(term['status'])}</code></div></div>
    <div class="kv"><div>{'Machine registry' if is_en else 'Registre machine'}</div><div><a href="/data/terms.json">/data/terms.json</a></div></div>
    <div class="kv"><div>{'Canonical manifest' if is_en else 'Manifest canonique'}</div><div><a href="/ig-manifest.json">/ig-manifest.json</a></div></div>
  </div>

  {related_html}

  <div class="footer">
    Last updated: {last_updated}<br/>
    This site is intentionally non-operational: it does not contain scoring weights, thresholds, calibrated protocols, datasets, or execution tooling.<br/>
    Primary doctrinal surface: gautierdorval.com
  </div>
</main>
</body>
</html>
"""

def make_glossary_index(lang: str, terms: list[dict], doctrine_version: str, last_updated: str) -> str:
    is_en = lang == LANG_EN
    docs = read_json(DOCS_PATH)["documents"]
    doc = next(d for d in docs if d["id"] == "IG-DOC-GLOSSARY")
    v = doc["variants"][lang]
    canonical = SITE + v["url"]
    title = f"{v['title']} | Interpretive Governance"
    description = v["description"]

    hreflang_alt = hreflang_cluster(
        SITE + "/en/glossary",
        SITE + "/fr/glossaire",
        SITE + "/",
    )
    head_common = make_head_common(title, description, canonical, lang, hreflang_alt, doctrine_version)

    doc_meta = f"""
<meta name="ig:doc-id" content="{doc['id']}"/>
<meta name="ig:classification" content="{doc['classification']}"/>""".strip()

    graph = jsonld_website_person() + [
        jsonld_webpage(canonical, v["title"], description, lang, doc["classification"], doctrine_version, doc_id=doc["id"]),
    ]

    termset = {
        "@type": "DefinedTermSet",
        "@id": f"{canonical}#definedtermset",
        "name": v["title"],
        "inLanguage": lang,
        "isPartOf": {"@id": f"{SITE}/#website"},
        "hasDefinedTerm": [],
    }

    items_html: list[str] = []
    sorted_terms = sorted(terms, key=lambda t: t["variants"][lang]["label"].lower())
    for t in sorted_terms:
        label = t["variants"][lang]["label"]
        definition = t["variants"][lang]["definition"]
        slug = t["slug"]
        href = ("/en/terms/" if is_en else "/fr/termes/") + slug
        status = t["status"]
        status_badge = ""
        if status != "canonical":
            status_badge = f' <span class="badge badge--informative">{escape(status)}</span>'
        items_html.append(f'<li><a href="{href}"><strong>{escape(label)}</strong></a>{status_badge}: {escape(definition)}</li>')
        termset["hasDefinedTerm"].append({
            "@type": "DefinedTerm",
            "@id": f"{SITE}{href}#term",
            "url": f"{SITE}{href}",
            "name": label,
            "description": definition,
            "inLanguage": lang,
            "termCode": t["termCode"],
            "identifier": t["id"],
        })

    graph.append(termset)
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

    nav = make_topbar_nav(lang, "glossary", "/fr/glossaire" if is_en else "/en/glossary", "Français" if is_en else "English")
    badge_label = "normative" if is_en else "normatif"
    intro = (
        "Canonical doctrinal definitions with stable identifiers. This glossary is intentionally non-operational."
        if is_en
        else
        "Définitions doctrinales canoniques avec identifiants stables. Ce glossaire est volontairement non opérable."
    )

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
{head_common}
{doc_meta}
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
<header class="topbar">
  <div class="container">
    <div class="brand">
      <img src="/assets/logo.svg?v={ASSET_VERSION}" width="34" height="34" alt="Interpretive Governance"/>
      <div>
        <div><strong>Interpretive Governance</strong> <span class="badge">doctrinal</span></div>
        <div class="muted" style="font-size:13px">{'Personal conceptual reference. Not an implementation.' if is_en else 'Référence conceptuelle personnelle. Non opérable.'}</div>
      </div>
    </div>
    <nav>
{nav}
    </nav>
  </div>
</header>
<main class="container">
  <h1>{escape(v['title'])}</h1>
  <div class="docmeta">
    <span class="badge badge--normative">{badge_label}</span>
    <span class="muted">{'Doc ID' if is_en else 'ID doc'}: <code>{doc['id']}</code> · {'Doctrine' if is_en else 'Doctrine'} {doctrine_version} · {'Non-operational' if is_en else 'Non opérable'}</span>
  </div>

  <div class="card">
    <p>{escape(intro)}</p>
    <p class="muted">{'Tip' if is_en else 'Astuce'}: {('use the term pages for stable links and JSON-LD.' if is_en else 'utilise les pages de termes pour des liens stables et du JSON-LD.')}</p>
  </div>

  <h2>{'Terms' if is_en else 'Termes'}</h2>
  <div class="card">
    <ul>
      {chr(10).join(items_html)}
    </ul>
  </div>

  <div class="footer">
    Last updated: {last_updated}<br/>
    This site is intentionally non-operational: it does not contain scoring weights, thresholds, calibrated protocols, datasets, or execution tooling.<br/>
    Primary doctrinal surface: gautierdorval.com
  </div>
</main>
</body>
</html>
"""

def sitemap_url_entry(loc: str, alternates: dict[str, str], last_updated: str) -> str:
    lines = ["  <url>"]
    lines.append(f"    <loc>{xml_escape(loc)}</loc>")
    lines.append(f"    <lastmod>{last_updated}</lastmod>")
    lines.append("    <changefreq>monthly</changefreq>")
    for hl, href in alternates.items():
        lines.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{xml_escape(href)}"/>')
    lines.append("  </url>")
    return "\n".join(lines)

def build_sitemap(documents: list[dict], terms: list[dict], last_updated: str) -> str:
    entries: list[str] = []

    # Document pages
    for doc in documents:
        doc_id = doc.get("id")
        variants = doc.get("variants", {}) if isinstance(doc.get("variants"), dict) else {}

        # Build hreflang cluster
        if doc_id == "IG-DOC-ROOT":
            alts = {
                LANG_XDEFAULT: f"{SITE}/",
                LANG_EN: f"{SITE}/en/",
                LANG_FR: f"{SITE}/fr/",
            }
        else:
            en_url = SITE + variants[LANG_EN]["url"]
            fr_url = SITE + variants[LANG_FR]["url"]
            alts = hreflang_cluster(en_url, fr_url, f"{SITE}/")

        # Emit <url> entries for each loc we want indexed
        for loc in sorted(set(alts.values())):
            # Avoid adding the x-default selector twice if it maps to the same URL
            entries.append(sitemap_url_entry(loc, alts, last_updated))

    # Term pages
    for t in terms:
        alts = {
            LANG_EN: SITE + "/en/terms/" + t["slug"],
            LANG_FR: SITE + "/fr/termes/" + t["slug"],
            LANG_XDEFAULT: f"{SITE}/",
        }
        for loc in sorted(set(alts.values())):
            entries.append(sitemap_url_entry(loc, alts, last_updated))

    # Sort by loc for deterministic output
    entries_sorted = sorted(entries, key=lambda s: re.search(r"<loc>(.*?)</loc>", s).group(1))
    return """<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
""" + "\n".join(entries_sorted) + "\n</urlset>\n"

def build_manifest(documents: list[dict], terms: list[dict], doctrine_version: str, last_updated: str) -> dict:
    dist: list[dict] = []

    for doc in documents:
        for lang, v in doc.get("variants", {}).items():
            url = v["url"]
            full = SITE + ("/" if url == "/" else url)

            in_language = lang
            if lang == LANG_XDEFAULT:
                in_language = [LANG_EN, LANG_FR]

            dist.append({
                "@type": "DataDownload",
                "name": v["title"],
                "description": v["description"],
                "contentUrl": full,
                "encodingFormat": "text/html",
                "inLanguage": in_language,
                "identifier": doc["id"],
                "keywords": [doc["role"], doc["classification"], "doctrinal", doc["operability"], f"doctrine:{doctrine_version}"],
            })

    for t in terms:
        for lang, prefix in [(LANG_EN, "/en/terms/"), (LANG_FR, "/fr/termes/")]:
            dist.append({
                "@type": "DataDownload",
                "name": t["variants"][lang]["label"],
                "description": t["variants"][lang]["definition"],
                "contentUrl": SITE + prefix + t["slug"],
                "encodingFormat": "text/html",
                "inLanguage": lang,
                "identifier": t["id"],
                "keywords": [t["termCode"], t["classification"], t["status"], "DefinedTerm", "doctrinal", f"doctrine:{doctrine_version}"],
            })

    machine_files = [
        ("Canonical manifest", "/ig-manifest.json", "application/ld+json"),
        ("Terms registry", "/data/terms.json", "application/json"),
        ("Documents registry", "/data/documents.json", "application/json"),
        ("Well-known manifest", "/.well-known/ig-manifest.json", "application/ld+json"),
        ("Well-known terms registry", "/.well-known/ig-terms.json", "application/json"),
        ("Well-known documents registry", "/.well-known/ig-documents.json", "application/json"),
        ("LLMs discovery", "/llms.txt", "text/plain"),
        ("Sitemap", "/sitemap.xml", "application/xml"),
        ("Robots", "/robots.txt", "text/plain"),
        ("Humans", "/humans.txt", "text/plain"),
        ("Governance (repo)", "/GOVERNANCE.md", "text/markdown"),
        ("Content policy (repo)", "/CONTENT-POLICY.md", "text/markdown"),
        ("Copyright (repo)", "/COPYRIGHT.md", "text/markdown"),
    ]
    for name, path, fmt in machine_files:
        dist.append({
            "@type": "DataDownload",
            "name": name,
            "contentUrl": SITE + path,
            "encodingFormat": fmt,
            "identifier": path,
            "keywords": ["informative", "doctrinal", "non-operational", f"doctrine:{doctrine_version}"],
        })

    return {
        "@context": ["https://schema.org", {"ig": SITE + "/ns#"}],
        "@type": "Dataset",
        "@id": SITE + "/ig-manifest.json#dataset",
        "name": "Interpretive Governance canonical manifest",
        "description": "Machine-readable index of public doctrinal artifacts (non-operational) for Interpretive Governance.",
        "url": SITE + "/ig-manifest.json",
        "identifier": "ig-manifest",
        "version": doctrine_version,
        "dateModified": last_updated,
        "inLanguage": [LANG_EN, LANG_FR],
        "creator": {"@id": SITE + "/#person"},
        "isBasedOn": ["https://gautierdorval.com/"],
        "license": SITE + "/COPYRIGHT.md",
        "distribution": sorted(dist, key=lambda d: d.get("contentUrl", "")),
    }

def main() -> None:
    terms_json = read_json(TERMS_PATH)
    docs_json = read_json(DOCS_PATH)

    doctrine_version = terms_json["doctrineVersion"]
    last_updated = terms_json["generatedAt"]

    terms = terms_json["terms"]
    documents = docs_json["documents"]

    # Mirrors (.well-known)
    well_known = ROOT / ".well-known"
    well_known.mkdir(exist_ok=True)
    write(well_known / "ig-terms.json", json.dumps(terms_json, ensure_ascii=False, indent=2) + "\n")
    write(well_known / "ig-documents.json", json.dumps(docs_json, ensure_ascii=False, indent=2) + "\n")

    # Glossary index pages (generated)
    write(ROOT / "en" / "glossary.html", make_glossary_index(LANG_EN, terms, doctrine_version, last_updated))
    write(ROOT / "fr" / "glossaire.html", make_glossary_index(LANG_FR, terms, doctrine_version, last_updated))

    # Term pages (generated)
    term_by_id = {t["id"]: t for t in terms}
    terms_dir = ROOT / "en" / "terms"
    termes_dir = ROOT / "fr" / "termes"
    terms_dir.mkdir(parents=True, exist_ok=True)
    termes_dir.mkdir(parents=True, exist_ok=True)

    for t in terms:
        write(terms_dir / f"{t['slug']}.html", make_term_page(t, LANG_EN, doctrine_version, last_updated, term_by_id))
        write(termes_dir / f"{t['slug']}.html", make_term_page(t, LANG_FR, doctrine_version, last_updated, term_by_id))

    # Sitemap (generated)
    write(ROOT / "sitemap.xml", build_sitemap(documents, terms, last_updated))

    # Manifest (+ mirror) (generated)
    manifest = build_manifest(documents, terms, doctrine_version, last_updated)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    write(ROOT / "ig-manifest.json", manifest_text)
    write(well_known / "ig-manifest.json", manifest_text)

if __name__ == "__main__":
    main()
