"""Vendored ColombiaCheck fetch/extraction helpers.

Vendored from v1 (`NLP-Fake-News-Colombia`, `colombiacheck_recon.py` @ 428dd76)
so this package has no import-time dependency on the v1 checkout. Two changes
against the original:

- The HTML cache directory is an explicit, root-anchored parameter instead of a
  CWD-relative global (v1 silently created a second cache when run from another
  directory).
- `extract_claimreview()` is trimmed: a census over all 2,941 JSON-LD payloads
  in the cached corpus found only `ClaimReview|Organization|Rating` nodes, so
  the original's `itemReviewed`/claimant and `Article`/`NewsArticle` branches
  were dead code and are gone.

The cache-key algorithm is byte-identical to v1's, so the corpus copied from
v1's `recon_cache/` is hit without refetching.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from evidence_retrieval_co.paths import CACHE_COLOMBIACHECK

# Identify yourself: polite scraping 101. Real contact, no spoofed agents.
HEADERS = {
    "User-Agent": (
        "evidence-retrieval-co/0.1 (academic research; "
        "contact: dsacris14723@universidadean.edu.co)"
    )
}
SLEEP_SECONDS = 1.5


def cache_key(url: str, suffix: str = ".html") -> str:
    """Map a URL to its on-disk cache filename.

    With the default suffix this is byte-identical to v1's algorithm, so the
    corpus copied from v1's `recon_cache/` resolves to cache hits.

    Args:
        url: Absolute URL of the page.
        suffix: File extension for the cache entry; override for non-HTML
            resources such as `robots.txt`.

    Returns:
        Cache filename: non-alphanumerics collapsed to `_`, truncated to 150
        characters, plus the suffix.
    """
    return re.sub(r"[^A-Za-z0-9]+", "_", url)[:150] + suffix


def get(
    url: str,
    session: requests.Session,
    cache_dir: Path = CACHE_COLOMBIACHECK,
    suffix: str = ".html",
    timeout: int = 30,
    retries: int = 3,
) -> str | None:
    """Fetch a resource politely, with an on-disk cache.

    Cache hits are plain file reads: no network access, no sleep. Cache misses
    make up to `retries` attempts with an identifying User-Agent, sleep
    `SLEEP_SECONDS` after each live request, and back off on failures.

    Args:
        url: Absolute URL to fetch.
        session: A `requests.Session`, reused across calls for keep-alive.
        cache_dir: Directory holding the cache; created if missing.
        suffix: Cache-file extension (see `cache_key`).
        timeout: Per-request timeout in seconds.
        retries: Attempts before giving up.

    Returns:
        The response body, or None on 404 or after all attempts fail.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / cache_key(url, suffix)
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            time.sleep(SLEEP_SECONDS)
            if resp.status_code == 200:
                cached.write_text(resp.text, encoding="utf-8")
                return resp.text
            if resp.status_code == 404:
                return None
            print(f"  [{resp.status_code}] retry {attempt + 1} for {url}")
            time.sleep(5 * (attempt + 1))
        except requests.RequestException as exc:
            print(f"  [error] {exc} -- retry {attempt + 1}")
            time.sleep(5 * (attempt + 1))
    return None


def _walk_jsonld(obj):
    """Yield every dict found inside a JSON-LD payload (handles `@graph`)."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_jsonld(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_jsonld(item)


def extract_claimreview(soup: BeautifulSoup) -> dict:
    """Pull ClaimReview fields from a page's JSON-LD blocks, if present.

    Args:
        soup: Parsed page.

    Returns:
        Dict with `claim_reviewed`, `rating`, `date_jsonld` and `jsonld_types`
        (pipe-joined sorted type set, or None). All values are None when the
        page carries no JSON-LD — true for 1,815 of the 4,756 cached articles.
    """
    out = {
        "claim_reviewed": None,
        "rating": None,
        "date_jsonld": None,
        "jsonld_types": [],
    }
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_jsonld(payload):
            t = node.get("@type")
            t_list = t if isinstance(t, list) else [t]
            t_list = [x for x in t_list if x]
            out["jsonld_types"] += t_list
            if "ClaimReview" in t_list:
                out["claim_reviewed"] = node.get("claimReviewed")
                rating = node.get("reviewRating") or {}
                out["rating"] = rating.get("alternateName") or rating.get(
                    "ratingValue"
                )
                out["date_jsonld"] = node.get("datePublished") or out["date_jsonld"]
    out["jsonld_types"] = "|".join(sorted(set(out["jsonld_types"]))) or None
    return out
