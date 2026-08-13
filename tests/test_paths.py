"""Path anchoring: every location must resolve from the repo root, not the CWD."""

from evidence_retrieval_co import paths


def test_root_is_repo_root():
    assert (paths.ROOT / "pyproject.toml").exists()


def test_cache_dir_is_root_anchored():
    # Regression for v1's CWD-relative Path("recon_cache") bug.
    assert paths.CACHE_COLOMBIACHECK.is_absolute()
    assert paths.CACHE_COLOMBIACHECK == paths.ROOT / "data" / "cache" / "colombiacheck"
