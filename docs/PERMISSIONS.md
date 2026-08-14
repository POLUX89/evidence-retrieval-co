# Permissions audit

Step 1 of ingestion is not writing a collector: it is asking, per domain, what
we are allowed to do. This table is that audit. The collector
(`src/evidence_retrieval_co/collect.py`) refuses any domain whose status here
is not **green**, and today **no domain is green** — so it fetches nothing.

**What we store right now: nothing.** Not one row is cleared. When a row turns
green, it must state what that clearance covers before any collection runs.

## How to read a verdict

| Status | Meaning |
|---|---|
| **green** | robots.txt **and** Terms of Service reviewed and compatible. Only these may be fetched. |
| **amber** | Partial or reactive opt-out. Consult, or request permission, before ingesting. |
| **red** | Refused: an explicit prohibition in the ToS, or a comprehensive anti-AI opt-out in robots.txt. |
| **pending** | Not yet reviewed. Treated exactly like red by the collector. |

Status was assigned by an explicit, conservative rule so it can be audited:
`red` when the Terms of Service prohibit mining/AI use, or when robots.txt
blocks 7 or more of the AI crawlers listed below; `amber` when it blocks
between 1 and 6; `pending` when no anti-AI clause was found — because absence
of a block is not permission, only absence of a machine-readable refusal.

## Principles (DESIGN.md §6)

- robots.txt is the **floor**; the Terms of Service weigh more legally. A green
  needs both.
- Indexing for internal use is not redistribution. **Neither is authorized by
  the mere absence of a block.**
- A partial opt-out gets the conservative reading. Exploiting a technical
  omission would honor the letter and violate the purpose.
- Never impersonate a permitted user-agent. Our collector identifies itself.
- Every row carries a **review date**: policies change, and a stale verdict is
  not a verdict.

Crawlers checked on every domain: `Google-Extended`, `GPTBot`, `ChatGPT-User`,
`CCBot`, `ClaudeBot`, `anthropic-ai`, `PerplexityBot`, `Applebot-Extended`,
`Bytespider`, `meta-externalagent`.

## Tier 1 operates under the inverse regime

**Ley 1712 de 2014** makes public information accessible by default and enables
a formal request with legal deadlines. Official sources also have downloadable
history, so tier 1 can be built without waiting for accumulation — it has no
clock. The press does: RSS has no archive, so what is not collected today will
not exist in three months (DESIGN.md §9).

## How this seed was built

Rows come from the source registry (`data/registry/source_registry.csv`): the
domains that account for 80% of citations in each tier — 24 press domains, and
50 institutions for official sources, grouped by entity because permission is
requested per organization, not per hostname. The robots.txt column was filled
by `src/evidence_retrieval_co/robots_audit.py`, which fetches **only**
`/robots.txt` (never article content) and whose raw results are in
`data/registry/robots_audit.csv`.

Deviation from the DESIGN.md §6 column list, stated so it is deliberate: the
"what I store" column is not repeated per row while it is uniformly nothing.
It becomes a per-row obligation as soon as a row turns green.

## What the audit found

- **robots.txt is missing on 36 of 74 domains**, nearly all `.gov.co`. That is
  not permission — it means there is no machine-readable restriction, and the
  Ley 1712 regime governs instead.
- **Anti-AI clauses are a press phenomenon**: 13 of the 14 domains that block
  AI crawlers are outlets. The exception is `cancilleria.gov.co`, the only
  official domain to do so — worth a formal request under Ley 1712.
- **The most-cited outlet is refused.** El Tiempo (827 articles) prohibits
  mining and AI training in its legal notice and blocks 8 crawlers.
- **The two strongest candidates are `elespectador.com` (596 articles) and
  `semana.com` (447)**: both without an anti-AI clause. They are where the ToS
  review should start.
- This confirms the structural bias DESIGN.md §6 predicted: outlets with legal
  capacity are the ones opting out, so the corpus will over-represent
  journalism without a dedicated data policy.

## Press (tier 2 — the one with a clock)

| Domain | Host | Articles | robots.txt | AI agents blocked | ToS (AI/mining) | Status | Reviewed |
|---|---|---:|---|---|---|---|---|
| eltiempo.com | — | 827 | partial | 8: GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Bytespider, meta-externalagent | prohibits AI/mining | **red** | 2026-08-14 |
| elespectador.com | — | 596 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| lasillavacia.com | — | 576 | partial | 10: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| semana.com | — | 447 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| elpais.com | — | 412 | partial | 4: CCBot, ClaudeBot, PerplexityBot, Bytespider | not reviewed | **amber** | 2026-08-14 |
| bbc.com | — | 400 | partial | 10: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| infobae.com | — | 358 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| elcolombiano.com | — | 272 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| caracol.com.co | — | 252 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| cnnespanol.cnn.com | — | 223 | partial | 10: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| portafolio.co | — | 199 | partial | 9: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| wradio.com.co | — | 194 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| larepublica.co | — | 174 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| rcnradio.com | — | 170 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| dw.com | — | 166 | partial | 10: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| bluradio.com | — | 163 | partial | 2: GPTBot, ChatGPT-User | not reviewed | **amber** | 2026-08-14 |
| nytimes.com | — | 152 | partial | 10: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| france24.com | — | 150 | allowed | 7: Google-Extended, GPTBot, ChatGPT-User, CCBot, ClaudeBot, anthropic-ai, PerplexityBot | not reviewed | **red** | 2026-08-14 |
| elpais.com.co | — | 141 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| reuters.com | — | 136 | blocked | 1: ChatGPT-User | not reviewed | **amber** | 2026-08-14 |
| elheraldo.co | — | 132 | partial | 5: GPTBot, CCBot, ClaudeBot, PerplexityBot, Bytespider | not reviewed | **amber** | 2026-08-14 |
| lafm.com.co | — | 105 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| cambiocolombia.com | — | 92 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| vanguardia.com | — | 87 | partial | 5: Google-Extended, GPTBot, ChatGPT-User, CCBot, anthropic-ai | not reviewed | **amber** | 2026-08-14 |

## Official sources (tier 1 — grouped by institution)

| Entity | Host | Articles | robots.txt | AI agents blocked | ToS (AI/mining) | Status | Reviewed |
|---|---|---:|---|---|---|---|---|
| funcionpublica.gov.co | — | 288 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| minsalud.gov.co | — | 236 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| secretariasenado.gov.co | — | 210 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| dane.gov.co | — | 165 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| corteconstitucional.gov.co | — | 157 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| camara.gov.co | — | 105 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| fiscalia.gov.co | — | 104 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| jep.gov.co | — | 83 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| comisiondelaverdad.co | — | 75 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| banrep.gov.co | — | 72 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| cancilleria.gov.co | — | 72 | partial | 7: Google-Extended, GPTBot, CCBot, ClaudeBot, Applebot-Extended, Bytespider, meta-externalagent | not reviewed | **red** | 2026-08-14 |
| suin-juriscol.gov.co | — | 68 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| senado.gov.co | leyes.senado.gov.co | 67 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| minhacienda.gov.co | — | 64 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| ins.gov.co | — | 63 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| altocomisionadoparalapaz.gov.co | — | 58 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| presidencia.gov.co | petro.presidencia.gov.co | 58 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| minciencias.gov.co | scienti.minciencias.gov.co | 56 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| centrodememoriahistorica.gov.co | — | 56 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| procuraduria.gov.co | — | 55 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| registraduria.gov.co | — | 52 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| policia.gov.co | — | 50 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| bogota.gov.co | — | 50 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| alcaldiabogota.gov.co | — | 47 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| dnp.gov.co | colaboracion.dnp.gov.co | 46 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| mindefensa.gov.co | — | 44 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| cortesuprema.gov.co | — | 41 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| invima.gov.co | — | 40 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| cne.gov.co | — | 38 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| colciencias.gov.co | scienti.colciencias.gov.co | 38 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| mintrabajo.gov.co | — | 37 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| defensoria.gov.co | — | 35 | allowed | none found | not reviewed | **pending** | 2026-08-14 |
| migracioncolombia.gov.co | — | 32 | not mentioned | none found | not reviewed | **pending** | 2026-08-14 |
| medicinalegal.gov.co | — | 28 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| contraloria.gov.co | — | 27 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| consejodeestado.gov.co | — | 26 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| secop.gov.co | community.secop.gov.co | 25 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| ramajudicial.gov.co | — | 25 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| contratos.gov.co | — | 25 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| mineducacion.gov.co | — | 25 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| imprenta.gov.co | svrpubindc.imprenta.gov.co | 25 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| minambiente.gov.co | — | 24 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| cali.gov.co | — | 23 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| unidadvictimas.gov.co | — | 23 | allowed | none found | not reviewed | **pending** | 2026-08-14 |
| mintic.gov.co | — | 22 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| prosperidadsocial.gov.co | — | 21 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| mininterior.gov.co | — | 19 | absent | none found | not reviewed | **pending** | 2026-08-14 |
| ideam.gov.co | — | 16 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| creg.gov.co | — | 13 | partial | none found | not reviewed | **pending** | 2026-08-14 |
| supersalud.gov.co | — | 12 | absent | none found | not reviewed | **pending** | 2026-08-14 |

## Next

Nothing may be collected until a row turns green, which requires reading the
Terms of Service — the part no script can do. Priority order is in
[`NEXT.md`](../NEXT.md).
