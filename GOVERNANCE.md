# Governance

This repository ships a static, machine-first doctrinal site.

The objective is to keep the public surface **stable, auditable, and non-operational** while remaining maximally legible to search engines and machine readers.

## DualWeb posture (doctrinal)

This site maintains two synchronized canonical surfaces:

- **Human surface**: HTML pages meant to be read, cited, and reviewed.
- **Machine surface**: a canonical manifest + registries meant to be discovered and parsed deterministically.

Public execution mechanics remain private by design.

## Canonical machine surfaces

- Canonical manifest: `/ig-manifest.json` (also mirrored at `/.well-known/ig-manifest.json`)
- Terms registry: `/data/terms.json` (also mirrored at `/.well-known/ig-terms.json`)
- Documents registry: `/data/documents.json` (also mirrored at `/.well-known/ig-documents.json`)
- Discovery file: `/llms.txt`

## Normative vs informative

Every indexable page MUST declare a classification:

- `normative`: defines meaning, boundaries, or requirements within the doctrine
- `informative`: explains, motivates, or contextualizes without defining requirements

This classification is expressed via:

- `<meta name="ig:classification" content="…">`
- JSON-LD `additionalProperty` values

## Canonical URL policy

- Canonical URLs are **clean** (no `.html`) and **HTTPS**.
- Internal links MUST use clean URLs:
  - ✅ `/principles`
  - ❌ `/principles.html`
- Every page MUST declare a canonical:
  - `<link rel="canonical" href="https://interpretive-governance.org/<path>">`

## Metadata policy (required)

Every indexable page MUST include:

- `<title>` (unique, includes the site name)
- `<meta name="description">` (unique per page)
- Open Graph + Twitter cards
- JSON-LD structured data (`application/ld+json`)
- IG meta:
  - `ig:doc-id` (or `ig:entity-id` for terms)
  - `ig:classification`
  - `ig:status` = `doctrinal`
  - `ig:operability` = `non-operational`
  - `ig:doctrine-version` = `0.2.0`

## Sitemap policy

- `sitemap.xml` MUST list canonical (clean) URLs only.
- If a page is indexable, it MUST be in the sitemap.
- If a page is non-indexable (e.g., 404), it MUST NOT be in the sitemap.

## Content boundaries

Public pages MUST NOT include:

- scoring formulas, weights, thresholds, calibrations
- reproducible operational tooling or client deliverables
- private datasets or test catalogs

(See `CONTENT-POLICY.md`.)

## Q-Layer (quality gates)

Run locally:

```bash
python scripts/quality_gate.py
```

The gate enforces:

- unique title + meta description across pages
- canonical URLs present and clean
- no internal `.html` links
- JSON-LD present on all pages
- IG classification and identifiers present on all pages
- term pages are consistent with `/data/terms.json`
- `ig-manifest.json` exists and references registries
- sitemap contains no `.html` URLs and covers all indexable pages
