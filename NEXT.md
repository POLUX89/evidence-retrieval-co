# Next

Written at session close, per DESIGN.md §9: sessions a week apart burn 30–40
minutes on re-immersion, so the next concrete task is written down while the
context is still loaded.

> **Priority rule: the RSS cron is the only task with a clock.** Press feeds
> have no archive — what is not collected today will not exist in three months.
> Tier 1 has downloadable history and can wait.

## 1. Review the Terms of Service for two outlets — the real bottleneck

`elespectador.com` (596 articles) and `semana.com` (447) are the strongest
candidates: neither has an anti-AI clause in robots.txt. Read their ToS looking
for text/data-mining, ML/AI training and archiving clauses. This is judgment,
not scripting — nothing else in phase 0 can finish until it is done.

## 2. Turn the first row green

Only after step 1, and only if the ToS allows it:

1. Find the outlet's real feed URL.
2. Update **both** `docs/PERMISSIONS.md` (status + what that clearance covers +
   review date) and `config/sources.yaml` (`audit_status`, `rss_url`). They must
   never disagree.
3. Replace `test_repo_config_has_no_green_sources` in `tests/test_collect.py`
   with a consistency check between the table and the config — the bootstrap
   invariant "nothing is green" stops being true and must stop being asserted.
4. `python -m evidence_retrieval_co.collect --dry-run` should now show one
   `WOULD FETCH`.

## 3. First real collection run

Run the collector for real, into `data/raw/` (immutable, never overwritten —
DESIGN.md §5). Then schedule it: that is the deliverable that closes phase 0.

## 4. Open decisions carried from the design doc

- **§11.3 — formal requests.** El Tiempo prohibits mining outright
  (`notificaciones@eltiempo.com`); Blu Radio is amber. New: `cancilleria.gov.co`
  is the only official domain blocking AI crawlers, and Ley 1712 gives a formal
  petition route with legal deadlines. Decide whether to send or drop.
- **§11.5 — claim matcher.** Similarity threshold and the concrete aggregation
  rule. Both are editorial decisions disguised as hyperparameters (§4D), so
  they go in the README when chosen.

## 5. Lower priority

- Manual review pass over the source registry via
  `data/registry/registry_overrides.csv` — the `other` tier (15.3% of links)
  is where the judgment calls live.
- Recover verdicts for the 1,815 cached articles without JSON-LD by reading the
  wrapper's CSS class; the registry builder already parses it.
- Before any new full-text harvest of ColombiaCheck, email
  `contacto@colombiacheck.com` — standing rule carried from v1.

## Status

Phase 0 is **in progress**: the audit exists and the collector is gated, but no
domain is cleared and nothing is being collected, so phase 0 is not closed.
D1 (scaffold + design docs) and D2 (source registry) are done.
