# Evidence-Backed Verification Assistant — Design Document (v2)

**Project:** evolution of [`NLP-Fake-News-Colombia`](https://github.com/POLUX89/NLP-Fake-News-Colombia)
**Status:** design. v1 complete and published; v2 system not yet implemented.
**Document date:** August 13, 2026

> **Bootstrap note (provenance).** Authored in Spanish on 2026-08-13; the
> verbatim original is preserved in [`DESIGN.es.md`](DESIGN.es.md) as a
> drift-guard. This English translation is the **normative** version. Editorial
> changes made at bootstrap (2026-08-13) are confined to blockquotes marked
> **Bootstrap note** — everything else is a faithful translation of the
> original.

---

## 1. What it is and what it is not

**It is** an assistant that, given a statement in Spanish, retrieves and shows
relevant evidence from a curated corpus — prioritizing primary sources — and,
subordinately, estimates how a professional fact-checker would label it.

**It is not** a truth detector or a "fake-news detector". It has no *ground
truth*: it has published expert judgments and measures agreement with them.

Operational formulation: **fact-checker-judgment predictor + evidence
retriever**, not a veracity classifier.

### Product change relative to v1

| | v1 (built) | v2 (design) |
|---|---|---|
| Input | claim text | claim text + corpus |
| Product | label | **evidence**; label secondary |
| Basis of the decision | learned style/topic | logical relation to documents |
| ColombiaCheck label | training target | evaluation reference |

---

## 2. Empirical motivation (v1's own results)

v2 is not born of an aesthetic preference but of a measured result:

| Model | macro-F1 (test) | Falso | Cuestionable | Verdadero |
|---|---|---|---|---|
| TF-IDF + LogReg | 0.386 | 0.743 | 0.351 | 0.065 |
| BETO (weighted loss) | **0.405** | 0.806 | 0.410 | **0.000** |

- BETO barely beats bag-of-words (+0.02 on test; 95% CI [0.371, 0.440]).
- `Verdadero` is unlearnable: 93 examples, declining (33 in 2020 → 2 in 2026).
- The EDA shows `petro`, `video` and `colombia` topping **all three classes**:
  topic does not separate the verdict.

**Conclusion:** classifying veracity from claim text does not work, and it is
not a model-capacity problem. The necessary signal is not in the claim; it is
in the external evidence. That is v2's design argument.

This negative result, honestly reported, is the project's central narrative
asset.

---

## 3. The *ground truth* problem and its safeguards

ColombiaCheck's labels are journalistic judgment with a public methodology: a
valuable noisy reference, not ground truth. (Careful formulation: a
*methodological limitation*, not a challenge to the outlet's credibility.)

Safeguards:

1. **Multi-fact-checker triangulation.** Via ClaimReview, incorporate AFP
   Factual, EFE Verifica, La Silla Vacía, Chequeado. Compute κ between
   fact-checkers on shared claims → the reference **human ceiling**.
2. **Soft labels / flagged exclusion** where fact-checkers disagree.
3. **First-class abstention.** An NEI class ("not enough evidence") +
   threshold-based selective prediction. Conformal prediction (MAPIE) as a
   refinement.
4. **Measured calibration.** ECE and reliability diagrams on every release.
5. **Label auditing** with confident learning (cleanlab) → review queue.
6. **The author's own κ** on ~100 claims, to validate the scale mapping.
7. **Evidence always visible**, with source and date.
8. **Symmetry test** (§7) before any release.

**Metrics:** macro-F1, quadratic weighted κ (ordinal classes), confusion
matrix, bootstrap for minority classes. Never accuracy alone: the majority
baseline sits around 76%.

κ is **always reported relative to the human ceiling**. A κ of 0.45 against a
ceiling of 0.55 is a good result; without that context it invites misreadings.

---

## 4. Architecture

```
claim
  │
  ├─► [A] Check-worthiness router
  │        ├─ verifiable factual ────────► full path
  │        ├─ value judgment ────────────► evidence and context, NO label
  │        └─ out of scope ──────────────► explained refusal
  │
  ├─► [B] Retrieval (temporal cutoff + tier boost)
  │        BM25 + bi-encoder → RRF fusion → (cross-encoder rerank) → top-k
  │
  ├─► [C] Per-passage NLI  (k independent runs)
  │        mDeBERTa-XNLI → entailment / contradiction / neutral
  │
  ├─► [D] Aggregation (explicit, documented rule)
  │
  └─► [E] Output: EVIDENCE first; label as a subordinate chip
```

### [A] Router — a safety requirement, not an optional improvement

Canonical example: *"The minimum wage was bad policy"* **must not receive a
label**. It is a value judgment; no evidence can verify it. Labeling it
"False" turns the tool into a political instrument.

Initial implementation: zero-shot LLM ("is this verifiable with data, or is it
an evaluation?"). It resolves ~90% of cases without training anything. Later
replaceable by a trained classifier (CLEF CheckThat! task 1 has Spanish data).

### [B] Retrieval

- **Hybrid is mandatory:** BM25 is irreplaceable for figures, dates and proper
  names, which is what claims abound in. Fuse with **RRF**, not by summing
  scores.
- **No retriever training at first.** Zero-shot multilingual models
  (`multilingual-e5-base`, `BGE-m3`) perform well. Measure `recall@50` against
  BM25 as the baseline before considering fine-tuning.
- **E5 prefixes:** E5 models require `"query: "` and `"passage: "`. Without
  them they underperform and nothing fails visibly.
- **Two separate passes: tier 1 and tier 2.** That way it is always known
  whether an official pronouncement existed, instead of the press displacing
  official sources in a single ranking. An empty tier-1 pass is information,
  not an error.
- **Mandatory temporal cutoff:** only evidence prior to the fact-check, plus a
  blocklist of fact-checker domains. Without this, the system *reads the
  answer* and the agreement is circular.
- **Chunking:** 200–400 tokens with overlap, respecting paragraph boundaries.
  It determines quality more than the choice of model.

### [C] NLI

A pretrained model, no fine-tuning, no GPU. Run **k times**, once per retrieved
passage — the most similar passage is not always the most informative. Cosine
similarity measures topical resemblance; NLI measures logical relation.

Output translation: contradiction → the evidence refutes; entailment → it
supports; neutral → *this passage says nothing about it* (≠ "questionable").

### [D] Aggregation — the most important design decision

Options: simple majority · informative-first (ignore neutrals unless
everything is neutral) · weighting by confidence and/or similarity · evidence
threshold (≥2 concordant passages).

**This rule is editorial policy disguised as a hyperparameter.** "One strong
contradiction suffices" produces an aggressive system; "I require a majority
of 3" produces a cautious one. Neither is neutral. It goes explicitly in the
README.

Weight by **source diversity**: three passages from the same outlet are one
voice, not three pieces of evidence.

An additional legitimate output: **"mixed / disputed evidence"**. When outlets
of different editorial lines contradict each other, that *is* the finding.
Forcing a verdict would be the error.

### [E] Interface

- Evidence on top, with source and date; label below, discreet.
- **Visually distinguish** a retrieved human verdict (v1: claim matching) from
  a system-generated one (v2). They look identical on screen and carry
  different responsibilities.
- A permanent disclaimer, not only in the README.
- The system explains why it does *not* answer when it abstains.

---

## 5. Corpus

### Tiers

| Tier | Content | Access path | Frequency |
|---|---|---|---|
| 1 | DANE, BanRep, `.gov.co`, DNP, Contraloría, Registraduría | Socrata APIs, portals, downloads | monthly/quarterly |
| 1b | Trade associations (Fedegán, Fedearroz, Fedecafé) | portals | variable |
| 2 | Press | RSS / sitemap | daily |

Trade associations publish primary data but **are interested parties**: mark
as "source with declared interest", never pure tier 1.

**Structural conflict of interest:** when the claim is *about the government*,
the government is not a neutral primary source. It requires counterweights
(Contraloría, multilaterals, academia) or explicit marking of the conflict in
the output.

### How to derive the source registry without being an expert in every sector

Extract the URLs cited by ~500 ColombiaCheck fact-checks and count domains per
topic. Without knowing agriculture, MinAgricultura, Agronet, ICA and DANE's
ENA emerge. **v1's recon data (4,756 fact-checks) already enables this.**

> **Bootstrap note (correction).** "Already enables this" holds only because
> the git-untracked local HTML cache from v1's recon was preserved and copied
> into this repo's local `data/cache/colombiacheck/` (provenance in
> [`DATASHEET.md`](DATASHEET.md)). No CSV column carries the cited URLs, and a
> census of all 2,941 JSON-LD payloads in the corpus found zero citation keys
> (`citation`, `isBasedOn`, `references`) — extraction requires parsing the
> article-body HTML, filtering boilerplate by DOM containment. A fresh clone
> without that local cache cannot run this step without re-harvesting.

Warning: this inherits ColombiaCheck's authority criterion into the retrieval
layer, where it is no longer visible. Audit the list and complement it with
sources they do not cite.

### Construction

```
raw/         immutable, never overwritten (irreversible: RSS has no history)
processed/   normalization, canonical-URL dedup, chunking
index/       embeddings + metadata (domain, date, tier, category, URL)
```

Changing the embedding model or the chunking = rebuild from `raw/`, without
re-collecting.

**Sufficient scale: 10,000–50,000 passages.** Millions are not needed; what is
needed is that the right ones are there.

---

## 6. Data governance and permissions

**Step 1 of ingestion is not writing code: it is the per-domain permissions
audit.** A versioned table in the repo:

`domain | RSS? | robots.txt | ToS (AI/mining clause) | what I store | review date`

### Findings already verified

| Outlet | Situation | Decision |
|---|---|---|
| **El Tiempo** | Explicit legal notice: prohibits text and data mining, ML/AI/LLM development, archived datasets and commercial use. Allowlist with `Google-Extended: Allow` | **Out of the corpus.** Request permission at `notificaciones@eltiempo.com` |
| **Semana** | No anti-AI clause in robots.txt; `Disallow` only on technical routes | Candidate. Verify ToS |
| **Blu Radio** | Blocks `GPTBot` and `ChatGPT-user`; no mention of other AI bots. No `/rss` | **Amber** (partial, reactive opt-out). Consult before ingesting |

`Allow: /rss/` does **not** mean "RSS only": in robots.txt, what is not
prohibited is allowed. The absence of `Disallow` on articles is the relevant
datum.

User-agents to look for on every domain: `Google-Extended`, `GPTBot`, `CCBot`,
`ClaudeBot`, `anthropic-ai`, `PerplexityBot`, `Applebot-Extended`.

### Principles

- robots.txt is the **floor**; ToS carry more legal weight.
- Indexing (internal use) ≠ redistribution. Neither is authorized by the mere
  absence of a block.
- Partial opt-out → conservative reading. Exploiting the technical omission
  would honor the letter and violate the purpose.
- Never impersonate a permitted user-agent.
- Record the **review date**: policies change.

### Tier 1 operates under an inverse regime

**Ley 1712 de 2014** (transparency law) makes public information accessible by
default and enables formal requests with legal deadlines. Moreover, tier 1
**has downloadable history**: it can be built today, without waiting for
accumulation.

### Induced structural bias

If the outlets with legal capacity are the ones adding anti-AI clauses, the
corpus overrepresents outlets without a data policy. **The corpus will not be
a sample of Colombian journalism, but of Colombian journalism without a legal
department dedicated to AI.** State it that bluntly in the limitations.

---

## 7. Political bias

The hard case is not factual claims — outlets rarely contradict a DANE figure
— but evaluative and causal ones. That is why the router (§4A) resolves most
of the problem before it reaches the NLI.

Additional safeguards:

- **Source hierarchy** (§5): many claims resolve against the original datum
  without needing the press.
- **Audited index balance**, using an external, citable taxonomy of editorial
  orientation (Baly et al.), not the author's own criterion.
- **Transparency of the dispute**: show who contradicts and who supports.
- **Symmetry test** — a release prerequisite: equivalent claims about figures
  of opposite political sign must receive comparable treatment. Stratify
  errors by actor and topic.

**Beware false balance:** symmetry of treatment does not imply symmetry of
veracity. Including "both sides" does not apply when one side contradicts
verifiable official data.

---

## 8. MLOps

The versioned artifact **is no longer a trained classifier**; it is a
**retrieval configuration**: embedding model + chunking + hybrid weights +
tier boost + reranker + aggregation rule + thresholds.

It is wrapped as a custom `mlflow.pyfunc` and registered in the Model
Registry. The app loads `stage=Production` — a pattern v1 already implements
by loading from the HF Hub.

### Experiment metrics

Evidence `recall@k` · nDCG · proportion of tier 1 retrieved · domain diversity
· abstention rate · latency · **κ as secondary**.

### New-version triggers

- A new embedding model to compare
- A change of chunking or hybrid weights
- **Corpus growth** (the real, continuous trigger; re-indexing ≡ retraining)
- Monitored degradation: the "no evidence" rate rises or the tier-1 proportion
  falls

### Promotion gates (AND)

1. Retrieval metrics ≥ champion on a **frozen holdout** (DVC)
2. Not worse on a recent prospective set
3. Calibration not degraded
4. No significant drop on any slice (topic, subject orientation, date, region)
5. Abstention rate in range (no cheating by abstaining from everything)
6. **Ethical gates:** do not promote if source diversity falls or if
   abstention on regional claims rises
7. **Manual human approval** on the stage transition

Deployment: shadow mode 2–4 weeks → swap → automatic rollback.

### Index versioning = an auditability requirement

The corpus **is** the model. Every run records: index hash + code commit + HF
model `revision`. If someone questions a three-month-old verdict, the evidence
that existed then must be reconstructible.

Adding or removing domains is an editorial decision: it goes into the version
log **with written justification**, not as a silent data commit.

> Risk: optimizing configurations against a ColombiaCheck-derived set
> converges toward their evidence criterion, run after run — bias enters
> through the optimization door even though nothing is trained. That is why
> the gates include metrics independent of their criterion.

This is MLOps without fine-tuning, and that is fine: a good share of
production AI systems today orchestrate pretrained components rather than
training them.

---

## 9. Roadmap

Budget: **2–3 h/week** (~10 h/month). Starting from a complete v1.

| Phase | Deliverable | Hours | Calendar time |
|---|---|---|---|
| **0** | Permissions audit + RSS cron running | 15–20 | 6–8 wk |
| **1** | Tier-1 corpus (official APIs) + normalization + chunking + index | 25–35 | 10–14 wk |
| **2** | Claim matcher over the existing corpus + evaluation + app | 20–30 | 8–12 wk |
| **3** | Router + NLI + aggregation + temporal cutoff | 30–40 | 12–16 wk |
| **4** | MLflow pyfunc + DVC + monitoring + gates | 25–35 | 10–14 wk |

**Total: 8–12 months.** Publishable milestone around month ~6 (phases 0–2).

### Priority rule

**The RSS cron is the only thing with a clock.** A corpus that does not start
accumulating today will not exist in three months; everything else can be
designed later. Tier 1 and the rest have no closing window.

### Fragmentation mitigation

2-hour sessions separated by 7 days burn 30–40 min on re-immersion. `NEXT.md`
with the next concrete task, written **when closing** each session · small
commits · a protected environment.

### Reading cadence

At most 1 reading session per 3 building sessions. Reading without building is
the most common way a project dies in the design phase.

---

## 10. What v1 already contributes

- `acquisition.py` — ClaimReview harvesting = seed-corpus builder
- Recon of 4,756 fact-checks → extraction of cited sources without new
  collection
- Frozen split (seed 42), bootstrap CIs, single evaluation on test
- Streamlit app loading a remote model → one step away from `stage=Production`
- Model Card · Datasheet · Data Statement · CI · pre-commit with `nbstripout`
- Selection bias already quantified: 61.8% ClaimReview coverage
- Demonstrated criterion: `rating` (structured markup) over `verdict` (fragile
  first-match heuristic)

> **Bootstrap note (superseded).** The original closed this section with "v2
> is a branch of this repo, not a new project." The bootstrap decision
> (2026-08-13) is the opposite: v2 lives in this **separate repository**
> (`evidence-retrieval-co`), cross-linked with v1. Rationale: v1 is a
> finished, citable artifact (tag `v0.1.0`, published model and live demo)
> whose story should stay closed; v2 is a different product with a different
> stack and data lifecycle; and the same-repo reuse benefit was overstated —
> v1 is not cleanly importable (its collection code is vendored here instead),
> and the local cache had to be copied once either way. See also the
> correction in §5 on what "without new collection" actually requires.

---

## 11. Open decisions

1. **Political scope.** A system that issues judgments on national political
   claims, built and publicly deployed by an active-duty officer, has
   implications beyond the technical (the restriction on political
   deliberation for the military in Colombia is constitutional). A
   methodologically defensible option: **exclude national partisan politics**
   and focus on non-partisan misinformation — health, disasters, fraud,
   science — where the technical problem is identical. **A pending, conscious
   decision**, not an omission.
2. **v1's public demo.** Currently online, with a correct disclaimer. A
   screenshot circulates without it. Decide explicitly whether it stays
   active.
3. Formal request to El Tiempo (and Blu): send or discard.
4. Repository language for the v2 documentation.
5. Claim-matcher similarity threshold and concrete aggregation rule.

> **Bootstrap note (resolutions, 2026-08-13).** Decision 1: **resolved** — the
> scope excludes national partisan politics; the project focuses on
> non-partisan misinformation (health, disasters, fraud, science). Decision 2:
> **resolved** — the v1 demo stays up, with its disclaimer. Decision 4:
> **resolved** — English; this translation is normative and the Spanish
> original is archived as [`DESIGN.es.md`](DESIGN.es.md). Decisions 3 and 5
> remain **open** and are tracked in [`NEXT.md`](../NEXT.md).

---

## 12. Limitations to declare from day one

- There is no *ground truth*; only agreement with expert judgments.
- Selection bias: fact-checkers check what is viral-and-dubious; the system is
  not for scanning general news.
- A corpus incomplete due to outlet opt-outs, biased toward outlets without a
  data policy.
- Asymmetric abstention: less official statistics on rural topics, the
  informal economy and peripheral territories → "not enough evidence"
  concentrates where the State records less.
- Cadence mismatch: monthly tier 1 vs. daily press → recent claims resolve
  with tier 2.
- The "questionable" class (manipulation by omitted context) is the hardest
  and the worst covered; if it gets collapsed, say so as a limitation, not as
  a technical simplification.
- NLI models trained on XNLI (translations) underperform on colloquial
  Colombian speech → more "neutral" for certain speakers.
- NLI artifacts: negations trigger "contradiction" without reasoning.
- Out of scope: longitudinal analysis of Colombian media coverage (it requires
  a representativeness that opt-outs preclude).

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| **Scope.** Three projects disguised as one | Publishable milestone at month 6; phases 3–4 are improvements, not requirements |
| **Collision with the master's thesis** | The thesis has priority; only phase 0 runs in parallel |
| **Authority laundering** (screenshots of "the AI says FALSE") | Disclaimer in the UI, evidence first, abstention by default on private individuals |
| **Transparency theater** | Deliberate friction: readable evidence, source and date visible |
| **PII in logs** from the free-text field | Retention policy + filter for claims about non-public persons (Ley 1581) |
| **Over-engineering as an alibi** | Explicit hours reserved for the model card and limitations |
| **Memorization in published weights** | Declare the assumption in the Datasheet |

---

## 14. References

**Automated fact-checking**

- Guo, Schlichtkrull & Vlachos (2022). *A Survey on Automated Fact-Checking*. TACL.
- Schlichtkrull, Guo & Vlachos (2023). *AVeriTeC*. NeurIPS.
- Thorne et al. (2018). *FEVER*. NAACL.
- Glockner, Hou & Gurevych (2022). *Missing Counter-Evidence Renders NLP Fact-Checking Unrealistic*. EMNLP.
- Nakov et al. (2021). *Automated Fact-Checking for Assisting Human Fact-Checkers*. IJCAI.
- Hassan et al. (2017). *ClaimBuster*. VLDB.
- Konstantinovskiy et al. (2021). *Toward Automated Factchecking*. Digital Threats.
- Kazemi et al. (2021). *Claim Matching Beyond English*. ACL.
- Barrón-Cedeño et al. CLEF CheckThat! Lab.

**Retrieval**

- Karpukhin et al. (2020). *Dense Passage Retrieval*. EMNLP.
- Thakur et al. (2021). *BEIR*. NeurIPS.
- Cormack et al. (2009). *Reciprocal Rank Fusion*. SIGIR.
- Lin, Nogueira & Yates (2021). *Pretrained Transformers for Text Ranking*.
- Wang et al. (2022). *GPL*. NAACL.

**NLI**

- Bowman et al. (2015). *SNLI*. EMNLP.
- Conneau et al. (2018). *XNLI*. EMNLP.
- Gururangan et al. (2018). *Annotation Artifacts in NLI Data*. NAACL.

**Labels, agreement and calibration**

- Cohen (1960, 1968). Agreement coefficients.
- Aroyo & Welty (2015). *Truth Is a Lie*. AI Magazine.
- Uma et al. (2021). *Learning from Disagreement: A Survey*. JAIR.
- Northcutt, Jiang & Chuang (2021). *Confident Learning*. JAIR.
- Guo et al. (2017). *On Calibration of Modern Neural Networks*. ICML.
- Angelopoulos & Bates (2023). *Conformal Prediction: A Gentle Introduction*.
- Lim (2018). *Checking How Fact-checkers Check*. Research & Politics.

**Sources, media bias and governance**

- Baly et al. (2018). *Predicting Factuality of Reporting and Bias of News Media Sources*. EMNLP.
- Baly et al. (2020). *We Can Detect Your Bias*. EMNLP.
- Longpre et al. (2024). *Consent in Crisis: The Rapid Decline of the AI Data Commons*.
- Mitchell et al. (2019). *Model Cards for Model Reporting*. FAT*.
- Bender & Friedman (2018). *Data Statements for NLP*. TACL.
- Gebru et al. (2021). *Datasheets for Datasets*. CACM.
- Wardle & Derakhshan (2017). *Information Disorder*. Council of Europe.
- RFC 9309 — Robots Exclusion Protocol.
- Ley 1712 de 2014 (transparency) · Ley 1581 de 2012 (habeas data).

**Interaction and trust**

- Bansal et al. (2021). *Does the Whole Exceed its Parts?*. CHI.
- Buçinca, Malaya & Gajos (2021). *To Trust or to Think*. CSCW.
- Uscinski & Butler (2013). *The Epistemology of Fact Checking*. Critical Review.

**Engineering**

- Huyen (2022). *Designing Machine Learning Systems*. O'Reilly.
- Sculley et al. (2015). *Hidden Technical Debt in ML Systems*. NeurIPS.
- Wilson et al. (2017). *Good Enough Practices in Scientific Computing*. PLOS CB.
- Barbaresi (2021). *Trafilatura*. ACL demos.
- Cañete et al. (2020). *Spanish Pre-Trained BERT Model* (BETO). PML4DC.

---

## Guiding principle

> The system does not say what is true. It shows what the sources say, from
> what date, and with what degree of agreement — and it acknowledges when it
> cannot rule.
>
> What distinguishes a serious project from a naive one is not eliminating
> bias: it is measuring it, exposing it, and not pretending neutrality.
