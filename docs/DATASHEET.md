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

## Source registry (derived artifact)

`data/registry/source_registry.csv` is the one committed derivation of the seed:
which domains the fact-checks cite, how often, and in how many articles. It is
domain-level only — `domain, tier, role, n_links, n_articles,
scope_flag_partisan, conflict_flag_government, sample_urls` (at most three
sample URLs) — and contains **no article text**, the same stance v1 took.

Built by `src/evidence_retrieval_co/source_registry.py`, fully offline:

1. Iterate the 4,756 article pages (listing pages excluded by filename).
2. Select the article-body container positionally
   (`div.row.<verdict>.text-articulos > div.col-12.col-md-9` → its longest
   attribute-less child `<div>`, skipping the `#datos-claves` summary box).
3. Keep the `<a href>` links inside it. **DOM containment does the filtering**;
   the small residue of share/contact links is removed by URL pattern
   (`/sharer/`, `/intent/`, `t.me/share/url`, `whatsapp://send`, `mailto:`) and
   never by bare domain — `t.me`, `wa.me`, `instagram.com` and
   `ifcncodeofprinciples.poynter.org` all appear as genuine in-body citations.
4. Normalize to a host, assign a role and a tier, aggregate, sort by
   `(-n_links, domain)`.

JSON-LD is not used: a census of all 2,941 payloads in the corpus found zero
citation keys (`citation`, `isBasedOn`, `references`).

**Result (2026-08-13):** 4,756 articles parsed, 0 container failures, **6,577
domains** across **88,668 links** (~18.6 per article).

| Tier | Domains | Links | % |
|---|---:|---:|---:|
| social | 56 | 20,216 | 22.8 |
| archive | 14 | 14,489 | 16.3 |
| other | 5,156 | 13,528 | 15.3 |
| fact-checker | 22 | 10,895 | 12.3 |
| press | 114 | 10,111 | 11.4 |
| official-co | 547 | 8,226 | 9.3 |
| platform | 63 | 6,118 | 6.9 |
| intl-org | 188 | 2,697 | 3.0 |
| academic | 410 | 1,957 | 2.2 |
| civil-society | 6 | 410 | 0.5 |
| interested-party | 1 | 21 | 0.0 |

Roles record what a link *does*: `internal` (self-references), `claim-source`
(social platforms — usually the claim under review, not evidence), `archive`
(snapshots), `tool` (search, media forensics, file hosting — the checker's
method) and `evidence` (everything else).

### The two flags mark, they do not reclassify

`scope_flag_partisan` marks party, campaign and politicians' personal sites —
outside this project's non-partisan scope. `conflict_flag_government` marks the
government's own voice: the presidency and vice-presidency families, which
DESIGN.md §5 identifies as **not neutral primary sources when the claim is about
the government**.

Both stay flags rather than tiers on purpose. The presidency publishes each
administration under its own subdomain of the official domain —
`petro.presidencia.gov.co` (Petro), `id.`/`idm.` (Duque), `wp.`/`wsp.` (Santos),
with `presidencia.gov.co` as the canonical site — and those subdomains carry
decrees, bills and official communications.

**They stay in tier 1 deliberately.** An official publication is bound by legal
and institutional standards, and it is frequently the primary record itself: a
decree published there *is* the decree. The flag is therefore **not a doubt
about accuracy**. It marks a different property — when the claim is about the
government's own conduct or results, the government is not a neutral arbiter of
it — and §5 asks for exactly that: a counterweight (control bodies, courts,
multilaterals, academia) or an explicit marking in the output. Tier answers
"how authoritative is this source?"; the flag answers "authoritative about
*whom*?".

Scope boundary, stated so it is auditable: the flag covers the presidency and
vice-presidency families only. Ministries are executive too, but the corpus
cites them mostly for technical data (epidemiology, statistics); whether to
widen the flag to them is an open judgment call, as is the treatment of
state-owned companies beyond the single `interested-party` tier.

**Corrections** go in `data/registry/registry_overrides.csv`
(`domain,tier_override,scope_flag_override,reason`), which the builder merges on
every run — the generated CSV is never hand-edited, so re-running reproduces it
byte-for-byte. The overrides file may introduce tier values the code does not
know (`civil-society`, `interested-party`).

Reproduce with the local seed present:

```bash
python -m evidence_retrieval_co.source_registry --top 40
```

### Known limitations

- **Archive links hide their sources.** Snapshot services are 16.3% of links,
  and short forms like `archive.is/lMm9i` carry no recoverable original URL, so
  an offline pipeline cannot attribute them. They are counted as `archive`, not
  as the outlet they preserve.
- **`other` is 15.3% of links and means "needs human judgment"**, not "junk":
  it holds legal-text mirrors, Wikipedia, and 3,793 domains cited exactly once.
  Nothing downstream should treat it as a source tier.
- **Partisan flagging is coarse by construction.** It catches 14 domains / 69
  links (party, campaign and politicians' personal sites). Claims about
  politicians arrive as social-platform links, so the real non-partisan scope
  filter is topic-level routing (DESIGN.md §4A), not this flag. The presidency's
  administration subdomains are deliberately **not** flagged here — they are
  institutional publications and carry `conflict_flag_government` instead.
- **Government voice is marked, not excluded:** 18 domains / 476 links across
  four administrations (`presidencia.gov.co` and its `petro.`, `id.`, `idm.`,
  `wp.`, `wsp.`, `es.`, `historico.`, `dapre.` subdomains, plus
  `vicepresidencia.gov.co`). They stay `official-co`; downstream retrieval is
  what must require a counterweight.
- **Interested parties need manual marking.** State-owned companies and trade
  associations publish primary data with a declared interest (DESIGN.md §5);
  only `ecopetrol.com.co` is marked so far, and ministries are not covered by
  the government-voice flag.
- **The registry inherits ColombiaCheck's authority criterion**, which is the
  warning in DESIGN.md §5: it must be audited and complemented with sources they
  do not cite, not adopted as-is.

## robots.txt audit (derived artifact)

`data/registry/robots_audit.csv` records what each audited domain's robots.txt
grants, for the 74 domains that seed [`PERMISSIONS.md`](PERMISSIONS.md). Built
by `src/evidence_retrieval_co/robots_audit.py`, which fetches **only**
`/robots.txt` — never article content — with the same identified, throttled,
cached fetcher used for the corpus. Fetched 2026-08-14; raw files are cached in
the git-ignored `data/cache/robots/`.

Unlike the source registry, this is a **dated snapshot, not a reproducible
derivation**: policies change, which is precisely why every row carries a review
date. Re-running it against the cache reproduces the same table; re-running it
against the live web is a new audit.

Columns: `domain, entity, tier, robots_found, wildcard_verdict,
ai_agents_blocked, has_ai_clause, feed_hint, checked_date`. Only verdicts are
committed, never the fetched files.

## Distribution & maintenance

The cache and raw tables are **not distributed** — they stay local and
git-ignored, the same copyright stance as v1 (only derived, domain-level
artifacts are committed). A fresh clone can rebuild the seed by re-running a
polite harvest; before any new full-text harvest, contact
`contacto@colombiacheck.com`. This datasheet is updated whenever the seed or
its derivations change.
