#!/usr/bin/env python3
"""
Build deterministic machine-first artifacts from canonical registries.

Source of truth:
- data/terms.json
- data/documents.json

Outputs:
- ig-manifest.json (+ /.well-known mirror)
- sitemap.xml
- glossary.html / glossaire.html
- terms/* and termes/* pages (+ JSON-LD)
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

ASSET_VERSION = "20260226-2"  # bump when assets change

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def pv(property_id: str, value: str) -> dict:
    return {"@type": "PropertyValue", "propertyID": property_id, "value": value}

def truncate(s: str, max_len: int=175) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    cut = s[:max_len-1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"

def jsonld_website_person() -> list[dict]:
    return [
        {
            "@type": "WebSite",
            "@id": f"{SITE}/#website",
            "url": f"{SITE}/",
            "name": "Interpretive Governance",
            "description": "Doctrinal reference for bounded interpretation and auditable machine responses (non-operational).",
            "inLanguage": ["en", "fr"],
            "publisher": {"@id": f"{SITE}/#person"},
        },
        {
            "@type": "Person",
            "@id": f"{SITE}/#person",
            "name": "Gautier Dorval",
            "url": "https://gautierdorval.com/",
            "sameAs": ["https://gautierdorval.com/", "https://github.com/GautierDorval/gautierdorval-identity"],
        },
    ]

def jsonld_webpage(canonical: str, name: str, description: str, lang: str, classification: str, doctrine_version: str, doc_id: str | None = None, entity_id: str | None = None, page_type: str="WebPage") -> dict:
    props = [
        {"@type":"PropertyValue","propertyID":"ig:classification","value":classification},
        {"@type":"PropertyValue","propertyID":"ig:status","value":"doctrinal"},
        {"@type":"PropertyValue","propertyID":"ig:operability","value":"non-operational"},
        {"@type":"PropertyValue","propertyID":"ig:doctrine-version","value":doctrine_version},
    ]
    if doc_id:
        props.insert(0, {"@type":"PropertyValue","propertyID":"ig:doc-id","value":doc_id})
    if entity_id:
        props.insert(0, {"@type":"PropertyValue","propertyID":"ig:entity-id","value":entity_id})
    return {
        "@type": [page_type, "Article"] if page_type != "ProfilePage" else page_type,
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": name,
        "description": description,
        "isPartOf": {"@id": f"{SITE}/#website"},
        "inLanguage": lang,
        "dateModified": read_json(TERMS_PATH).get("generatedAt"),
        "author": {"@id": f"{SITE}/#person"},
        "about": {"@type":"Thing","name":"Interpretive Governance"},
        "additionalProperty": props,
    }

def jsonld_defined_term(term: dict, lang: str, canonical: str, termset_id: str, doctrine_version: str) -> dict:
    v = term["variants"][lang]
    props = [
        {"@type":"PropertyValue","propertyID":"ig:entity-id","value":term["id"]},
        {"@type":"PropertyValue","propertyID":"ig:termCode","value":term["termCode"]},
        {"@type":"PropertyValue","propertyID":"ig:entity-status","value":term["status"]},
        {"@type":"PropertyValue","propertyID":"ig:classification","value":term["classification"]},
        {"@type":"PropertyValue","propertyID":"ig:doctrine-version","value":doctrine_version},
    ]
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
        "additionalProperty": props,
    }

def make_head_common(title: str, description: str, canonical: str, lang: str, hreflang_alt: dict[str,str], doctrine_version: str, og_type: str="article") -> str:
    og_locale = "en_US" if lang == "en" else "fr_CA"
    hreflang_links = "\n".join([f'<link rel="alternate" hreflang="{hl}" href="{url}"/>' for hl, url in hreflang_alt.items()])
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
<meta property="og:locale" content="{og_locale}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{escape(title)}"/>
<meta name="twitter:description" content="{escape(description)}"/>
<meta name="twitter:image" content="{SITE}/assets/og.png"/>"""

def make_topbar_nav(lang: str, active: str, lang_switch_href: str, lang_switch_label: str) -> str:
    if lang == "en":
        items = [
            ("home", "Home", "/"),
            ("principles", "Principles", "/principles"),
            ("architecture", "Architecture", "/architecture"),
            ("scope", "Scope", "/scope"),
            ("glossary", "Glossary", "/glossary"),
            ("author", "Author &amp; governance", "/author"),
            ("notes", "Notes", "/notes"),
        ]
    else:
        items = [
            ("home", "Accueil", "/"),
            ("principles", "Principes", "/principes"),
            ("architecture", "Architecture", "/architecture"),
            ("scope", "Portée", "/portee"),
            ("glossary", "Glossaire", "/glossaire"),
            ("author", "Auteur &amp; gouvernance", "/author"),
            ("notes", "Notes", "/notes"),
        ]
    links = []
    for key, label, href in items:
        cls = "active" if key == active else ""
        links.append(f'<a class="{cls}" href="{href}">{label}</a>')
    links.append(f'<a href="{lang_switch_href}">{lang_switch_label}</a>')
    return "\n".join(links)

def make_term_page(term: dict, lang: str, doctrine_version: str, last_updated: str, term_by_id: dict[str,dict]) -> str:
    is_en = lang == "en"
    label = term["variants"][lang]["label"]
    definition = term["variants"][lang]["definition"]
    prefix = "/terms/" if is_en else "/termes/"
    other_prefix = "/termes/" if is_en else "/terms/"
    canonical = SITE + prefix + term["slug"]
    title = f"{label} | {'Glossary' if is_en else 'Glossaire'} | Interpretive Governance"
    description = truncate(definition)
    hreflang_alt = {"en": SITE + "/terms/" + term["slug"], "fr": SITE + "/termes/" + term["slug"]}
    head_common = make_head_common(title, description, canonical, lang, hreflang_alt, doctrine_version)
    entity_meta = f"""
<meta name="ig:classification" content="normative"/>
<meta name="ig:entity-type" content="DefinedTerm"/>
<meta name="ig:entity-id" content="{term['id']}"/>
<meta name="ig:termCode" content="{term['termCode']}"/>
<meta name="ig:entity-status" content="{term['status']}"/>""".strip()

    termset_id = f"{SITE}/glossary#definedtermset" if is_en else f"{SITE}/glossaire#definedtermset"
    graph = jsonld_website_person() + [
        jsonld_webpage(canonical, label, description, lang, "normative", doctrine_version, entity_id=term["id"]),
        jsonld_defined_term(term, lang, canonical, termset_id, doctrine_version),
    ]
    jsonld = json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False)

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
    is_en = lang == "en"
    docs = read_json(DOCS_PATH)["documents"]
    doc = next(d for d in docs if d["id"] == "IG-DOC-GLOSSARY")
    v = doc["variants"][lang]
    canonical = SITE + v["url"]
    title = f"{v['title']} | Interpretive Governance"
    description = v["description"]
    hreflang_alt = {"en": SITE + "/glossary", "fr": SITE + "/glossaire"}
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
        href = ("/terms/" if is_en else "/termes/") + slug
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
    jsonld = json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False)

    nav = make_topbar_nav(lang, "glossary", "/glossaire" if is_en else "/glossary", "Français" if is_en else "English")
    badge_label = "normative" if is_en else "normatif"
    intro = (
        "Canonical doctrinal definitions with stable identifiers. This glossary is intentionally non-operational."
        if is_en else
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

def sitemap_url_entry(loc: str, alternates: dict[str,str], last_updated: str) -> str:
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
    # docs
    for doc in documents:
        alts: dict[str,str] = {}
        for hl, v in doc["variants"].items():
            url = v["url"]
            alts[hl] = SITE + ("/" if url == "/" else url)
        for _, full in alts.items():
            entries.append(sitemap_url_entry(full, alts, last_updated))
    # terms
    for t in terms:
        alts = {"en": SITE + "/terms/" + t["slug"], "fr": SITE + "/termes/" + t["slug"]}
        for _, full in alts.items():
            entries.append(sitemap_url_entry(full, alts, last_updated))

    entries_sorted = sorted(entries, key=lambda s: re.search(r"<loc>(.*?)</loc>", s).group(1))
    return """<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
""" + "\n".join(entries_sorted) + "\n</urlset>\n"

def build_manifest(documents: list[dict], terms: list[dict], doctrine_version: str, last_updated: str) -> dict:
    dist: list[dict] = []

    for doc in documents:
        for lang, v in doc["variants"].items():
            url = v["url"]
            full = SITE + ("/" if url == "/" else url)
            dist.append({
                "@type": "DataDownload",
                "name": v["title"],
                "description": v["description"],
                "contentUrl": full,
                "encodingFormat": "text/html",
                "inLanguage": lang,
                "additionalProperty": [
                    pv("ig:doc-id", doc["id"]),
                    pv("ig:role", doc["role"]),
                    pv("ig:classification", doc["classification"]),
                    pv("ig:status", "doctrinal"),
                    pv("ig:operability", doc["operability"]),
                    pv("ig:doctrine-version", doctrine_version),
                ],
            })

    for t in terms:
        for lang, prefix in [("en","/terms/"), ("fr","/termes/")]:
            dist.append({
                "@type": "DataDownload",
                "name": t["variants"][lang]["label"],
                "description": t["variants"][lang]["definition"],
                "contentUrl": SITE + prefix + t["slug"],
                "encodingFormat": "text/html",
                "inLanguage": lang,
                "additionalProperty": [
                    pv("ig:entity-id", t["id"]),
                    pv("ig:termCode", t["termCode"]),
                    pv("ig:entity-type", "DefinedTerm"),
                    pv("ig:classification", t["classification"]),
                    pv("ig:entity-status", t["status"]),
                    pv("ig:status", "doctrinal"),
                    pv("ig:doctrine-version", doctrine_version),
                ],
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
            "additionalProperty": [
                pv("ig:classification", "informative"),
                pv("ig:status", "doctrinal"),
                pv("ig:operability", "non-operational"),
                pv("ig:doctrine-version", doctrine_version),
            ],
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
        "inLanguage": ["en", "fr"],
        "creator": {"@id": SITE + "/#person"},
        "isBasedOn": ["https://gautierdorval.com/"],
        "license": SITE + "/COPYRIGHT.md",
        "distribution": sorted(dist, key=lambda d: d.get("contentUrl","")),
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

    # Glossary index pages
    write(ROOT / "glossary.html", make_glossary_index("en", terms, doctrine_version, last_updated))
    write(ROOT / "glossaire.html", make_glossary_index("fr", terms, doctrine_version, last_updated))

    # Term pages
    term_by_id = {t["id"]: t for t in terms}
    terms_dir = ROOT / "terms"
    termes_dir = ROOT / "termes"
    terms_dir.mkdir(exist_ok=True)
    termes_dir.mkdir(exist_ok=True)

    for t in terms:
        write(terms_dir / f"{t['slug']}.html", make_term_page(t, "en", doctrine_version, last_updated, term_by_id))
        write(termes_dir / f"{t['slug']}.html", make_term_page(t, "fr", doctrine_version, last_updated, term_by_id))

    # Sitemap
    write(ROOT / "sitemap.xml", build_sitemap(documents, terms, last_updated))

    # Manifest (+ mirror)
    manifest = build_manifest(documents, terms, doctrine_version, last_updated)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    write(ROOT / "ig-manifest.json", manifest_text)
    write(well_known / "ig-manifest.json", manifest_text)

if __name__ == "__main__":
    main()
