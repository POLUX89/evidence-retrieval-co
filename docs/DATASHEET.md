# Datasheet — Evidence Corpus Seed (v2)

Follows Gebru et al., *Datasheets for Datasets* (CACM 2021), for the local
corpus seed this project starts from. The registry derived from it is
documented in the "Source registry" section (added with deliverable D2).

## Motivation

v2 needs (a) a seed corpus of professional fact-checks to mine for cited
sources (design §5) and later for claim matching (design §9, phase 2), and
(b) traceable provenance for every byte of it. The seed is the corpus v1
harvested from ColombiaCheck; no new collection was performed for the
bootstrap.

## Composition

Local-only, git-ignored (never committed, never redistributed):

| Item | Path | Count / size |
|---|---|---|
| Cached HTML pages | `data/cache/colombiacheck/` | 5,756 files, 750 MB |
| — article pages | filename not matching `_page_<N>.html` | 4,756 |
| — listing pages | `*_page_<N>.html` | 1,000 |
| Claims table | `data/raw/claims.csv` | 4,756 rows + header |
| v1 recon outputs | `data/raw/v1_recon/` | `chequeos_recon.csv`, `run_meta.json` |

`claims.csv` columns: `url, verdict, claim_reviewed, rating, pub_date,
jsonld_types, has_claimreview`. 2,941 of the 4,756 articles (61.8%) carry
ClaimReview JSON-LD; for the rest, the verdict is recoverable from the article
wrapper's CSS class. A `podcast` wrapper class exists: some `/chequeos` entries
are podcast episodes, not fact-checks.

## Collection process

Harvested by v1's recon (`colombiacheck_recon.py`): polite, throttled (1.5 s
between requests), cached, with an identifying User-Agent carrying a real
contact address, honoring robots.txt. Harvest completed 2026-07-20
(`run_meta.json`: `run_at` 2026-07-20T14:11:38, `n_listing` 4756).

**Copy provenance:** copied 2026-08-13 from the v1 working tree
(`NLP-Fake-News-Colombia` @ commit `428dd76`, tag `v0.1.0`) by byte-preserving
`rsync`; counts verified against the table above. The v1 fetcher/extractor is
vendored in `src/evidence_retrieval_co/colombiacheck.py` with a byte-identical
cache-key algorithm, so the copied cache resolves to cache hits without any
refetching.

## Uses

- Deliverable D2: offline extraction of in-body cited domains → the committed
  `data/registry/source_registry.csv` (domains, counts, sample URLs — no
  article text).
- Roadmap phase 2: claim matching against published fact-checks.
- NOT for: training a veracity classifier (v1's measured dead end), or
  redistribution of ColombiaCheck content.

## Distribution & maintenance

The cache and raw tables are **not distributed** — they stay local and
git-ignored, the same copyright stance as v1 (only derived, domain-level
artifacts are committed). A fresh clone can rebuild the seed by re-running a
polite harvest; before any new full-text harvest, contact
`contacto@colombiacheck.com`. This datasheet is updated whenever the seed or
its derivations change.
