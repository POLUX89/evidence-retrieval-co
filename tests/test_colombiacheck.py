"""Vendored fetcher/extractor: cache-key compatibility and offline behavior."""

from bs4 import BeautifulSoup

from evidence_retrieval_co import colombiacheck


def test_cache_key_matches_v1_algorithm():
    url = "https://colombiacheck.com/chequeos/10-departamentos-no-tienen-senador"
    assert colombiacheck.cache_key(url) == (
        "https_colombiacheck_com_chequeos_10_departamentos_no_tienen_senador.html"
    )


def test_cache_key_truncates_long_urls():
    key = colombiacheck.cache_key("https://example.com/" + "a" * 300)
    assert key.endswith(".html")
    assert len(key) == 150 + len(".html")


def test_get_uses_cache_without_network(tmp_path):
    url = "https://colombiacheck.com/chequeos/algo"
    (tmp_path / colombiacheck.cache_key(url)).write_text("<html>cached</html>")
    # A session without .get() would raise if the network path were touched.
    html = colombiacheck.get(url, session=object(), cache_dir=tmp_path)
    assert html == "<html>cached</html>"


def test_extract_claimreview_from_graph():
    payload = """
    <html><head><script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [{
        "@type": "ClaimReview",
        "claimReviewed": "An invented claim",
        "datePublished": "2024-10-08",
        "reviewRating": {"@type": "Rating", "alternateName": "Falso",
                         "ratingValue": "1", "bestRating": "5",
                         "worstRating": "1"},
        "author": {"@type": "Organization", "name": "Org",
                   "url": "https://org.example"}
    }]}
    </script></head><body></body></html>
    """
    out = colombiacheck.extract_claimreview(BeautifulSoup(payload, "lxml"))
    assert out["claim_reviewed"] == "An invented claim"
    assert out["rating"] == "Falso"
    assert out["date_jsonld"] == "2024-10-08"
    assert out["jsonld_types"] == "ClaimReview|Organization|Rating"


def test_extract_claimreview_absent():
    out = colombiacheck.extract_claimreview(
        BeautifulSoup("<html><body><p>plain</p></body></html>", "lxml")
    )
    assert out["claim_reviewed"] is None
    assert out["rating"] is None
    assert out["date_jsonld"] is None
    assert out["jsonld_types"] is None
