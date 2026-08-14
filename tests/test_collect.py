"""The permissions gate. No test performs network access."""

import pytest

from evidence_retrieval_co import collect
from evidence_retrieval_co.paths import SOURCES_YAML


def _source(status="pending", rss_url="https://example.test/rss"):
    return collect.Source(
        name="Example",
        domain="example.test",
        tier="press",
        audit_status=status,
        rss_url=rss_url,
    )


class RecordingFetcher:
    """Fetcher stub that records the URLs it was asked for."""

    def __init__(self):
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        return {"entries": []}


@pytest.mark.parametrize("status", ["pending", "amber", "red"])
def test_gate_refuses_every_non_green_status(status):
    with pytest.raises(collect.PermissionGateError) as exc:
        collect.assert_fetch_allowed(_source(status))
    message = str(exc.value)
    assert "example.test" in message
    assert status in message
    assert "PERMISSIONS.md" in message


def test_gate_runs_before_any_fetch():
    stub = RecordingFetcher()
    with pytest.raises(collect.PermissionGateError):
        collect.fetch_source(_source("amber"), fetcher=stub)
    assert stub.calls == []


def test_green_source_without_feed_is_still_refused():
    with pytest.raises(collect.PermissionGateError, match="no rss_url"):
        collect.assert_fetch_allowed(_source("green", rss_url=None))


def test_green_source_uses_the_injected_fetcher(monkeypatch):
    # Guard: the real path must not be reached, so feedparser stays optional.
    monkeypatch.setattr(
        collect, "_default_fetcher", lambda url: pytest.fail("network path used")
    )
    stub = RecordingFetcher()
    collect.fetch_source(_source("green"), fetcher=stub)
    assert stub.calls == ["https://example.test/rss"]


def test_load_sources_round_trip(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text(
        "version: 1\n"
        "sources:\n"
        "  - name: Example\n"
        "    domain: example.test\n"
        "    tier: press\n"
        "    audit_status: pending\n"
        "    rss_url: null\n"
        "    notes: synthetic\n"
    )
    (source,) = collect.load_sources(config)
    assert source.domain == "example.test"
    assert source.rss_url is None
    assert source.notes == "synthetic"


def test_load_sources_rejects_unknown_status(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text(
        "sources:\n  - name: Example\n    domain: example.test\n"
        "    tier: press\n    audit_status: verde\n"
    )
    with pytest.raises(ValueError, match="audit_status"):
        collect.load_sources(config)


def test_load_sources_rejects_missing_field(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text("sources:\n  - name: Example\n    tier: press\n    audit_status: green\n")
    with pytest.raises(ValueError, match="domain"):
        collect.load_sources(config)


def test_repo_config_has_no_green_sources():
    """Bootstrap invariant: the collector provably fetches nothing.

    Replace this with a consistency check against docs/PERMISSIONS.md once the
    first domain is cleared.
    """
    sources = collect.load_sources(SOURCES_YAML)
    assert sources, "the shipped configuration should not be empty"
    assert all(s.audit_status != "green" for s in sources)
    assert all(s.rss_url is None for s in sources)


def test_dry_run_refuses_everything_and_exits_clean(capsys, monkeypatch):
    monkeypatch.setattr(
        collect, "_default_fetcher", lambda url: pytest.fail("network path used")
    )
    code = collect.main(["--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "WOULD FETCH" not in out
    assert out.count("REFUSED") == len(collect.load_sources(SOURCES_YAML))
    assert "0 of" in out
    assert "no network access performed" in out
