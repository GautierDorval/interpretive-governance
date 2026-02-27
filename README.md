# interpretive-governance

A personal doctrinal showcase of **Interpretive Governance** (non-operational conceptual framework), published at **interpretive-governance.org**.

## Canonical doctrinal anchors

- https://gautierdorval.com/
- https://gautierdorval.com/.well-known/ai-governance.json
- https://github.com/GautierDorval/gautierdorval-identity

## Canonical machine surfaces (DualWeb)

- Manifest: `https://interpretive-governance.org/ig-manifest.json` (also `https://interpretive-governance.org/.well-known/ig-manifest.json`)
- Terms registry: `https://interpretive-governance.org/data/terms.json` (also `https://interpretive-governance.org/.well-known/ig-terms.json`)
- Documents registry: `https://interpretive-governance.org/data/documents.json` (also `https://interpretive-governance.org/.well-known/ig-documents.json`)
- Discovery file: `https://interpretive-governance.org/llms.txt`

## Scope

This repository intentionally excludes:

- scoring formulas, weights, thresholds, calibrations
- reproducible audit protocols, test catalogs, datasets
- implementation playbooks, deployment scripts, operational tooling

## Publishing

Static site intended for Cloudflare Pages.

Build settings:

- Framework preset: None
- Build command: (empty)
- Output directory: .

## Cache bust

Assets are versioned with `?v=20260227-1`.

## URL policy

Cloudflare Pages serves clean URLs (no `.html`). This repo enforces:

- Language roots: `/en/` and `/fr/` (root `/` is `x-default` selector)
- Clean internal links (no `.html`): `/en/principles` (not `/en/principles.html`)
- 301 canonicalization via `_redirects` (legacy paths and `.html` forms)
- `sitemap.xml` uses canonical clean URLs only
