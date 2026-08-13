"""Source-registry extraction, classification and determinism tests.

Everything runs on the synthetic fixtures from conftest.py, except the corpus
smoke test, which is skipped when the local cache is absent (fresh clones, CI).
"""

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from evidence_retrieval_co import source_registry as sr
from evidence_retrieval_co.paths import CACHE_COLOMBIACHECK, REGISTRY_CSV

NO_OVERRIDES = "no_such_overrides.csv"


def _links(html: str) -> list[str]:
    container = sr.select_body_container(BeautifulSoup(html, "lxml"))
    assert container is not None
    return sr.extract_links(container)


def test_iter_skips_listing_pages(tmp_path):
    (tmp_path / "an_article.html").write_text("<html></html>")
    (tmp_path / "https_colombiacheck_com_chequeos_page_3.html").write_text(
        "<html></html>"
    )
    assert [p.name for p in sr.iter_article_files(tmp_path)] == ["an_article.html"]


def test_verdict_from_wrapper_class(article_html, listing_html):
    assert sr.extract_verdict(BeautifulSoup(article_html, "lxml")) == "falso"
    assert sr.extract_verdict(BeautifulSoup(listing_html, "lxml")) is None


def test_listing_page_has_no_container(listing_html):
    assert sr.select_body_container(BeautifulSoup(listing_html, "lxml")) is None


def test_datos_claves_skipped(datos_claves_html):
    # The key-facts box sits before the prose div; its link must not surface.
    assert _links(datos_claves_html) == ["https://www.minsalud.gov.co/synthetic-page"]


def test_boilerplate_outside_container_excluded(article_html):
    links = _links(article_html)
    assert "http://t.me/SynthOrg" not in links  # nav social icon
    assert "https://ifcncodeofprinciples.poynter.org/" not in links  # footer badge
    assert not any("relacionado-inventado" in url for url in links)  # related box


def test_pattern_residue_filtered_but_legit_kept(article_html):
    links = _links(article_html)
    assert not any("sharer" in url for url in links)
    assert not any("/intent/" in url for url in links)
    assert not any(url.startswith("mailto:") for url in links)
    assert not any("whatsapp" in url for url in links)
    assert not any("t.me/share" in url for url in links)
    # The same domains are legitimate when they are the cited content:
    assert "https://t.me/synthchannel/5" in links
    assert "https://www.instagram.com/p/synthpost/" in links


def test_relative_links_resolve_against_colombiacheck(article_html):
    assert "https://colombiacheck.com/chequeos/otro-chequeo-inventado" in _links(
        article_html
    )


def test_domain_normalization():
    assert sr.domain_of("https://WWW.Dane.GOV.co/x") == "dane.gov.co"
    assert (
        sr.domain_of("https://elecciones.registraduria.gov.co:81/a")
        == "elecciones.registraduria.gov.co"
    )


def test_role_classification():
    assert sr.classify_role("colombiacheck.com") == "internal"
    assert sr.classify_role("archivo.colombiacheck.com") == "internal"
    assert sr.classify_role("archive.ph") == "archive"
    assert sr.classify_role("web.archive.org") == "archive"
    for social in ("twitter.com", "x.com", "t.co"):
        assert sr.classify_role(social) == "claim-source"
    assert sr.classify_role("dane.gov.co") == "evidence"
    assert sr.classify_role("eltiempo.com") == "evidence"


def test_archive_alias_family_recognized():
    # archive.today serves the same snapshots under several ccTLDs.
    for alias in ("archive.md", "archive.vn", "archive.fo", "archive.li"):
        assert sr.classify_role(alias) == "archive"
        assert sr.infer_tier(alias, "archive") == "archive"


def test_subdomains_inherit_their_parent_classification():
    assert sr.classify_role("co.linkedin.com") == "claim-source"
    assert sr.infer_tier("espanol.cdc.gov", "evidence") == "intl-org"
    assert sr.infer_tier("news.un.org", "evidence") == "intl-org"
    assert sr.infer_tier("cnnespanol.cnn.com", "evidence") == "press"
    assert sr.classify_role("share.evernote.com") == "tool"


def test_verification_tools_are_not_sources():
    for tool in ("google.com", "lens.google.com", "tineye.com", "scribd.com"):
        assert sr.classify_role(tool) == "tool"
        assert sr.infer_tier(tool, "tool") == "platform"


def test_tier_inference():
    assert sr.infer_tier("dane.gov.co", "evidence") == "official-co"
    assert sr.infer_tier("who.int", "evidence") == "intl-org"
    assert sr.infer_tier("uniandes.edu.co", "evidence") == "academic"
    assert sr.infer_tier("eltiempo.com", "evidence") == "press"
    assert sr.infer_tier("maldita.es", "evidence") == "fact-checker"
    assert sr.infer_tier("redcheq.com", "evidence") == "fact-checker"
    assert sr.infer_tier("twitter.com", "claim-source") == "social"
    assert sr.infer_tier("archive.ph", "archive") == "archive"
    assert sr.infer_tier("example.test", "evidence") == "other"


def test_pubmed_is_academic_while_nih_stays_official():
    assert sr.infer_tier("pubmed.ncbi.nlm.nih.gov", "evidence") == "academic"
    assert sr.infer_tier("nih.gov", "evidence") == "intl-org"


def test_partisan_flag():
    assert sr.is_partisan("centrodemocratico.com") is True
    assert sr.is_partisan("apps.centrodemocratico.com") is True
    assert sr.is_partisan("ivanduque.com") is True
    assert sr.is_partisan("dane.gov.co") is False
    # The presidency's own site is an institutional source, not a campaign.
    assert sr.is_partisan("petro.presidencia.gov.co") is False
    assert sr.infer_tier("petro.presidencia.gov.co", "evidence") == "official-co"


def test_overrides_applied(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "one.html").write_text(
        '<div class="row falso text-articulos"><div class="col-12 col-md-9">'
        '<div><p><a href="https://confecamaras.org.co/x">invented</a></p></div>'
        "</div></div>"
    )
    overrides = tmp_path / "overrides.csv"
    overrides.write_text(
        "domain,tier_override,scope_flag_override,reason\n"
        "confecamaras.org.co,official-co,True,synthetic test override\n"
    )
    df, _ = sr.build_registry(cache, overrides)
    row = df.loc[df["domain"] == "confecamaras.org.co"].iloc[0]
    assert row["tier"] == "official-co"
    assert bool(row["scope_flag_partisan"]) is True


def test_registry_deterministic_and_ranked(tmp_path, article_html, datos_claves_html):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "a_first.html").write_text(article_html)
    (cache / "b_second.html").write_text(datos_claves_html)
    out1, out2 = tmp_path / "r1.csv", tmp_path / "r2.csv"
    for out in (out1, out2):
        df, stats = sr.build_registry(cache, tmp_path / NO_OVERRIDES)
        sr.write_registry(df, out)
        assert stats["n_container_missing"] == 0
    assert out1.read_bytes() == out2.read_bytes()

    df, _ = sr.build_registry(cache, tmp_path / NO_OVERRIDES)
    pairs = list(zip(df["n_links"], df["domain"]))
    assert pairs == sorted(pairs, key=lambda t: (-t[0], t[1]))
    assert list(df.columns) == sr.REGISTRY_COLUMNS


@pytest.mark.skipif(not REGISTRY_CSV.exists(), reason="registry not built yet")
def test_committed_registry_is_wellformed():
    df = pd.read_csv(REGISTRY_CSV)
    assert list(df.columns) == sr.REGISTRY_COLUMNS
    assert df["domain"].is_unique
    pairs = list(zip(df["n_links"], df["domain"]))
    assert pairs == sorted(pairs, key=lambda t: (-t[0], t[1]))
    assert (df["n_articles"] <= df["n_links"]).all()
    # Domain-level artifact only: sample URLs, never article text.
    assert df["sample_urls"].str.split("|").explode().str.startswith("http").all()


@pytest.mark.skipif(not CACHE_COLOMBIACHECK.exists(), reason="local corpus not present")
def test_corpus_smoke_real_markup_parses(tmp_path):
    # Small sample on purpose: enough to catch a selector regression against
    # real pages, short enough not to slow the local suite. The full-corpus
    # reproduction check is the CLI re-run documented in the Datasheet.
    df, stats = sr.build_registry(CACHE_COLOMBIACHECK, tmp_path / NO_OVERRIDES, limit=40)
    assert stats["n_parsed"] == 40
    assert stats["n_container_missing"] == 0
    assert len(df) > 0
    assert df["n_links"].sum() > 40  # real articles cite ~20 links each
