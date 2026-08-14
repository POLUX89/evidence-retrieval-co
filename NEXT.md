# Next

Written at session close, per DESIGN.md §9: sessions a week apart burn 30–40
minutes on re-immersion, so the next concrete task is written down while the
context is still loaded.

> **The clock is gone.** §9's priority rule — "the RSS cron is the only task
> with a clock" — assumed press feeds, which keep no archive. With tier 2
> deferred (2026-08-14), the corpus is built from tier 1 under Ley 1712, which
> has downloadable history. Nothing is deadline-bound now. That is freedom, and
> also the risk §9 names: without a forcing function, projects die in the design
> phase. Ship something small each session.

## 1. Work out how to access the top tier-1 institutions

The permissions question is settled by statute; the open question is the access
route. For the most-cited institutions in
[`PERMISSIONS.md`](docs/PERMISSIONS.md) — Función Pública, MinSalud, Secretaría
del Senado, DANE, Corte Constitucional — record for each:

- Is there an open-data portal or Socrata API (`datos.gov.co` is already in the
  registry), a bulk download, or only HTML pages?
- What is actually published: datasets, resolutions, bulletins, statistics?
- What we would store, which the table demands before a row turns green.

## 2. Complement the registry where it is blind

The registry inherits ColombiaCheck's authority criterion (DESIGN.md §5), so it
only knows sources they happened to cite. Measured gap: **health and science are
well covered** (WHO 521 citations, CDC 315, PubMed 320, plus Nature, The Lancet,
NEJM) but **disasters are nearly absent** — the whole `gestiondelriesgo.gov.co`
family has 13 citations and IDEAM 49. Since disasters are inside the declared
scope, UNGRD, IDEAM, SGC and the environmental authorities must be added
deliberately, not discovered.

## 3. Turn the first row green

Only after 1 and 2, for one institution:

1. Update **both** `docs/PERMISSIONS.md` (status, what the clearance covers,
   review date) and `config/sources.yaml`. They must never disagree.
2. Replace `test_repo_config_has_no_green_sources` in `tests/test_collect.py`
   with a consistency check between the table and the config — the bootstrap
   invariant "nothing is green" stops being true and must stop being asserted.
3. `python -m evidence_retrieval_co.collect --dry-run` should show one
   `WOULD FETCH`.

## 4. Reshape the collector for tier 1

`collect.py` is press-shaped: `rss_url` plus a `feedparser` fetcher. Tier 1
publishes through portals, APIs and bulk downloads. **Deliberately not
generalized yet** — the right abstraction is unknowable until step 1 shows what
the real access patterns are. Expect to rename `rss_url`, add an access method,
and possibly drop the `collect` extra's dependency.

## 5. Still open from the design doc

- **§11.5 — claim matcher.** Similarity threshold and the concrete aggregation
  rule. Both are editorial decisions disguised as hyperparameters (§4D), so they
  go in the README when chosen.
- §11.3 is **resolved**: no formal permission requests to the press.

## 6. Lower priority

- Manual review pass over the source registry via
  `data/registry/registry_overrides.csv` — the `other` tier (15.3% of links) is
  where the judgment calls live.
- Recover verdicts for the 1,815 cached articles without JSON-LD by reading the
  wrapper's CSS class; the registry builder already parses it.
- Before any new full-text harvest of ColombiaCheck, email
  `contacto@colombiacheck.com` — standing rule carried from v1.

## Status

Phase 0 is **in progress**: the audit exists and the collector is gated, but no
domain is cleared and nothing is being collected. Its deliverable is no longer
"RSS cron running" — it is a tier-1 source cleared and collecting. D1 (scaffold
+ design docs) and D2 (source registry) are done.
