# Governance

This repository ships a static, machine-first doctrinal site.

The objective is to keep the public surface **stable, auditable, and non-operational** while remaining maximally legible to search engines and machine readers.

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

## Quality gates

Run locally:

```bash
python scripts/quality_gate.py
```

The gate enforces:

- unique title + meta description across pages
- canonical URLs present and clean
- no internal `.html` links
- JSON-LD present on all pages
- sitemap contains no `.html` URLs and covers all indexable pages
