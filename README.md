# evidence-retrieval-co

[![CI](https://github.com/POLUX89/evidence-retrieval-co/actions/workflows/ci.yml/badge.svg)](https://github.com/POLUX89/evidence-retrieval-co/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An evidence-retrieval assistant for Colombian misinformation: given a claim in
Spanish, retrieve and show **sourced, dated evidence** from a curated corpus —
and only subordinately estimate how a professional fact-checker would label it.

> ⚠️ **What this project is — and is not.**
> This is **not** a truth detector nor a "fake-news detector". It has no ground
> truth: it retrieves evidence, shows who says what and since when, and measures
> agreement with published expert judgments. When the evidence is insufficient,
> it abstains — and says why. The full design, including its limitations, is in
> [docs/DESIGN.md](docs/DESIGN.md).

## Why v2

[v1 (`NLP-Fake-News-Colombia`)](https://github.com/POLUX89/NLP-Fake-News-Colombia)
measured the ceiling of classifying a fact-check verdict from claim text alone:

| Model | macro-F1 (test) | `Verdadero` F1 |
|---|---|---|
| TF-IDF + LogReg | 0.386 | 0.065 |
| BETO (fine-tuned, weighted loss) | **0.405** | **0.000** |

BETO barely beats bag-of-words, and the `Verdadero` class is unlearnable. The
conclusion is structural, not a matter of model capacity: **the signal is not
in the claim text; it is in the external evidence**. v2 is the redesign that
takes that measurement seriously — retrieval first, verdicts subordinate.

v1 artifacts: [repository](https://github.com/POLUX89/NLP-Fake-News-Colombia) ·
[model on Hugging Face](https://huggingface.co/polux89/beto-colombiacheck) ·
[live demo](https://beto-colombiacheck.streamlit.app).

## Scope

The project covers **non-partisan misinformation**: health, disasters, fraud
and science. National partisan politics is explicitly out of scope — a
deliberate decision recorded in [docs/DESIGN.md §11](docs/DESIGN.md) — and the
architecture routes value judgments away from labeling entirely.

## Status — bootstrap

| Deliverable | State |
|---|---|
| D1 · Scaffold, design doc, corpus seed, repo | done |
| D2 · Offline source registry from the cached corpus | done — [6,577 domains](data/registry/source_registry.csv) |
| D3 · Permissions audit + gated collector skeleton | done — [74 domains audited](docs/PERMISSIONS.md) |

Roadmap **phase 0** (permissions audit + RSS cron running) is in progress: the
audit exists and the collector is gated, but no domain is cleared yet, so
nothing is being collected. Next steps in [NEXT.md](NEXT.md).

The 8–12-month roadmap (phases 0–4) lives in [docs/DESIGN.md §9](docs/DESIGN.md).

## Repository structure

```
├── config/sources.yaml   # collector sources + audit status (gate input; D3)
├── data/
│   ├── cache/            # local corpus seed (git-ignored; see the Datasheet)
│   ├── raw/              # claims.csv + v1 recon outputs (git-ignored)
│   └── registry/         # committed: derived source registry (no article text)
├── docs/
│   ├── DESIGN.md         # normative design document (EN)
│   ├── DESIGN.es.md      # verbatim Spanish original (archival)
│   ├── DATASHEET.md      # corpus provenance and composition
│   └── PERMISSIONS.md    # per-domain permissions audit (D3)
├── src/evidence_retrieval_co/
└── tests/
```

## Usage

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"
pre-commit install
ruff check . && pytest -q
```

The local corpus seed (`data/cache/`, `data/raw/`) is **not** in the repo; see
[docs/DATASHEET.md](docs/DATASHEET.md) for provenance. Tests that need it skip
automatically on a fresh clone.

## Ethics & provenance

Data collection is gated: the collector refuses any domain whose per-domain
audit in [docs/PERMISSIONS.md](docs/PERMISSIONS.md) is not explicitly green.
The corpus seed was harvested politely (identified User-Agent, throttled,
cached) by v1; nothing under `data/cache/` or `data/raw/` is redistributed by
this repository.

## License

MIT — see [LICENSE](LICENSE).
