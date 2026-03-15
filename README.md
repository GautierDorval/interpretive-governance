# interpretive-governance

A personal doctrinal showcase of **Interpretive Governance** (non-operational conceptual framework), published at **interpretive-governance.org**.

## Canonical doctrinal anchors

- https://gautierdorval.com/
- https://gautierdorval.com/.well-known/ai-governance.json
- https://github.com/GautierDorval/gautierdorval-identity

## Hard public governance surfaces

- `https://interpretive-governance.org/ai-governance.json`
- `https://interpretive-governance.org/interpretation-policy.json`
- `https://interpretive-governance.org/response-legitimacy.json`
- `https://interpretive-governance.org/anti-plausibility.json`
- `https://interpretive-governance.org/output-constraints.json`
- `https://interpretive-governance.org/qlayer.json`

## Canonical machine surfaces (DualWeb)

- Manifest: `https://interpretive-governance.org/ig-manifest.json`
- AI manifest: `https://interpretive-governance.org/ai-manifest.json`
- Terms registry: `https://interpretive-governance.org/data/terms.json`
- Documents registry: `https://interpretive-governance.org/data/documents.json`
- Discovery: `https://interpretive-governance.org/llms.txt` and `https://interpretive-governance.org/llms-full.txt`
- Well-known mirrors under `/.well-known/` and `/well-known/`

## Scope

This repository intentionally excludes:

- scoring formulas, weights, thresholds, calibrations
- reproducible audit protocols, test catalogs, datasets
- implementation playbooks, deployment scripts, operational tooling

## Build and validation

```bash
python scripts/build_artifacts.py
python scripts/quality_gate.py
```

Doctrine version: 0.3.0
