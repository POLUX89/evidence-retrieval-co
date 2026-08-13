"""Canonical project paths, anchored to the repo root.

Single source of truth for filesystem locations. Because paths are derived from
this file's own location (not the current working directory), they resolve the
same from a notebook, a script, CI, or any other directory. The package is
installed editable (`pip install -e .`), so `from evidence_retrieval_co.paths
import CLAIMS_CSV` works anywhere.

v1's recon resolved its HTML cache relative to the CWD (`Path("recon_cache")`),
which silently created a second cache when run from another directory. Every
path here is anchored to ROOT so that cannot happen again.
"""

from __future__ import annotations

from pathlib import Path

# src/evidence_retrieval_co/paths.py -> parents[2] is the repo root.
ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
DATA_RAW = DATA / "raw"
DATA_CACHE = DATA / "cache"
DATA_REGISTRY = DATA / "registry"
CONFIG = ROOT / "config"
DOCS = ROOT / "docs"

# Well-known files and directories.
CACHE_COLOMBIACHECK = DATA_CACHE / "colombiacheck"
CLAIMS_CSV = DATA_RAW / "claims.csv"
REGISTRY_CSV = DATA_REGISTRY / "source_registry.csv"
REGISTRY_OVERRIDES = DATA_REGISTRY / "registry_overrides.csv"
SOURCES_YAML = CONFIG / "sources.yaml"

__all__ = [
    "CACHE_COLOMBIACHECK",
    "CLAIMS_CSV",
    "CONFIG",
    "DATA",
    "DATA_CACHE",
    "DATA_RAW",
    "DATA_REGISTRY",
    "DOCS",
    "REGISTRY_CSV",
    "REGISTRY_OVERRIDES",
    "ROOT",
    "SOURCES_YAML",
]
