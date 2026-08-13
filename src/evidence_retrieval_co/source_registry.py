"""Offline source registry: which domains do the cached fact-checks cite?

Deliverable D2 (docs/DESIGN.md §5): parse the locally cached ColombiaCheck
articles, extract the links their authors cite inside the article body, and
aggregate them into a ranked, committed registry of source domains
(`data/registry/source_registry.csv`). Runs fully offline over
`data/cache/colombiacheck/`; no article text is written to the registry.

Extraction strategy (validated by a census of the full corpus):

- Only links inside the article-body container are considered. The container
  is `div.row.<verdict>.text-articulos > div.col-12.col-md-9` → its longest
  attribute-less child `<div>` (the prose div has no id/class; an optional
  sibling `div#datos-claves` summary box is skipped). DOM containment alone
  removes navigation, share buttons, footer and badge boilerplate.
- The small residue of share/contact links that DO live inside the prose is
  dropped by URL pattern, never by bare domain: t.me, wa.me, instagram.com,
  tiktok.com and ifcncodeofprinciples.poynter.org all occur in the corpus as
  genuine in-body citations.
- JSON-LD is not consulted: the corpus census found zero citation keys
  (`citation`, `isBasedOn`, `references`) across all 2,941 payloads.

Each domain gets a role — what the link *does* in a fact-check (`internal`,
`archive`, `claim-source`, `tool`, `evidence`) — and a tier — what kind of
source it is (`fact-checker`, `archive`, `social`, `platform`, `official-co`,
`intl-org`, `academic`, `press`, `other`) — plus two flags that mark, rather
than reclassify: `scope_flag_partisan` (party/campaign sites, out of the
project's non-partisan scope) and `conflict_flag_government` (the government's
own voice, DESIGN.md §5). Both are heuristics: `other` means
"needs human judgment", and corrections go through
`data/registry/registry_overrides.csv` (see `apply_overrides`), never by
editing the generated CSV — the overrides file may also introduce tier values
the code does not know, such as `civil-society`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup, Tag

from evidence_retrieval_co import paths

BASE_URL = "https://colombiacheck.com"
LISTING_RE = re.compile(r"_page_\d+\.html$")

# Share/contact residue that appears INSIDE the prose container. Matched as
# URL substrings — never blocklist bare domains (see module docstring).
RESIDUE_PATTERNS = (
    "facebook.com/sharer/",
    "twitter.com/intent/",
    "t.me/share/url",
    "whatsapp://send",
    "api.whatsapp.com/send?text=",
    "mailto:",
)

ARCHIVE_DOMAINS = {
    # archive.today serves the same snapshots under many ccTLDs; the corpus
    # cites at least .is, .ph, .md, .vn and .fo.
    "archive.is",
    "archive.ph",
    "archive.today",
    "archive.md",
    "archive.vn",
    "archive.fo",
    "archive.li",
    "archive.org",
    "web.archive.org",
    "perma.cc",
    "ghostarchive.org",
}

# Social platforms: in fact-checks these are usually the claim under review
# (role `claim-source`), not corroborating evidence.
SOCIAL_DOMAINS = {
    "twitter.com",
    "x.com",
    "t.co",
    "facebook.com",
    "m.facebook.com",
    "instagram.com",
    "tiktok.com",
    "vt.tiktok.com",
    "youtube.com",
    "youtu.be",
    "t.me",
    "wa.me",
    "whatsapp.com",
    "api.whatsapp.com",
    "linkedin.com",
    "soundcloud.com",
    "ivoox.com",
    "threads.net",
    "bsky.app",
}

# Verification tooling and generic hosting: the domain is not the author of
# what is linked. These are the fact-checker's *method* (reverse image search,
# forensic checks, a file drop), not sources — the corpus must never ingest
# them. `google.com` alone accounts for 2,430 in-body links.
PLATFORM_DOMAINS = {
    # search / reverse image
    "google.com",
    "google.com.co",
    "lens.google.com",
    "yandex.com",
    "tineye.com",
    "bing.com",
    # media forensics
    "invid-project.eu",
    "fotoforensics.com",
    "hivemoderation.com",
    "sightengine.com",
    "wasitai.com",
    "virustotal.com",
    "detect.truemedia.org",
    # hosting, notes, documents
    "evernote.com",
    "scribd.com",
    "drive.google.com",
    "docs.google.com",
    "dropbox.com",
    "docdro.id",
    "issuu.com",
    "infogram.com",
    "wetransfer.com",
    # media hosting and misc tooling
    "spreaker.com",
    "open.spotify.com",
    "itunes.apple.com",
    "filmot.com",
    "crowdtangle.com",
    "doi.org",
    # shorteners
    "bit.ly",
    "tinyurl.com",
}

# International organizations and foreign official sources.
INTL_ORG_DOMAINS = {
    "who.int",
    "paho.org",
    "un.org",
    "unicef.org",
    "unhcr.org",
    "acnur.org",
    "oecd.org",
    "oecd-ilibrary.org",
    "ilo.org",
    "imf.org",
    "worldbank.org",
    "iadb.org",
    "cepal.org",
    "unesco.org",
    "cdc.gov",
    "nih.gov",
    "fda.gov",
    "medlineplus.gov",
    "whitehouse.gov",
    "europa.eu",
    "unodc.org",
    "oas.org",
    "ohchr.org",
    "icrc.org",
    "corteidh.or.cr",
    "fao.org",
    "undp.org",
}

ACADEMIC_DOMAINS = {
    "scielo.org",
    "scielo.org.co",
    "arxiv.org",
    "redalyc.org",
    "researchgate.net",
    "ssrn.com",
    "jstor.org",
    "semanticscholar.org",
    "medrxiv.org",
    "biorxiv.org",
    # Journals and literature indexes. `ncbi.nlm.nih.gov` is checked before
    # the intl-org set on purpose: PubMed is literature, while `nih.gov`
    # itself is a foreign official body.
    "ncbi.nlm.nih.gov",
    "nature.com",
    "thelancet.com",
    "nejm.org",
    "bmj.com",
    "jamanetwork.com",
    "sciencedirect.com",
    "springer.com",
    "plos.org",
    "mayoclinic.org",
}

FACTCHECKER_DOMAINS = {
    "maldita.es",
    "newtral.es",
    "factual.afp.com",
    "chequeado.com",
    "politifact.com",
    "snopes.com",
    "factcheck.org",
    "aosfatos.org",
    "animalpolitico.com",
    "poynter.org",
    "redcheq.com",
    "espaja.com",
    "cotejo.info",
}

PRESS_DOMAINS = {
    "eltiempo.com",
    "elespectador.com",
    "semana.com",
    "lasillavacia.com",
    "caracol.com.co",
    "caracoltv.com",
    "noticiascaracol.com",
    "rcnradio.com",
    "canalrcn.com",
    "noticiasrcn.com",
    "bluradio.com",
    "elcolombiano.com",
    "elheraldo.co",
    "elpais.com.co",
    "portafolio.co",
    "larepublica.co",
    "dinero.com",
    "wradio.com.co",
    "lafm.com.co",
    "pulzo.com",
    "publimetro.co",
    "elnuevosiglo.com.co",
    "lapatria.com",
    "vanguardia.com",
    "eluniversal.com.co",
    "infobae.com",
    "bbc.com",
    "bbc.co.uk",
    "cnn.com",
    "elpais.com",
    "nytimes.com",
    "reuters.com",
    "afp.com",
    "efe.com",
    "dw.com",
    "france24.com",
    "rtve.es",
    "verdadabierta.com",
    "cambiocolombia.com",
    "efectococuyo.com",
    "radionacional.co",
    "razonpublica.com",
    "apnews.com",
    "washingtonpost.com",
    "univision.com",
    "elmundo.es",
    "lavanguardia.com",
    "swissinfo.ch",
    "larepublica.pe",
    "theguardian.com",
    "vozdeamerica.com",
    "cuestionpublica.com",
    "ambitojuridico.com",
}

# Partisan-political domains: party, campaign and politicians' personal sites.
# Flagged, never dropped — the scope filter (non-partisan misinformation) is
# applied downstream, and dropping silently would hide it from audit.
#
# Domain-level flagging is coarse and catches little (14 domains, 69 links in
# the corpus): politicians' claims arrive as social-platform links, and the
# real filter is topic-level routing (docs/DESIGN.md §4A).
#
# Deliberate exclusion: the presidency publishes each administration under its
# own subdomain of its official domain — `petro.` (Petro), `id.`/`idm.`
# (Duque), `wp.`/`wsp.` (Santos) — while `presidencia.gov.co` is the canonical
# site. Those subdomains serve decrees, bills and official communications, so
# they are institutional, not campaign sites: they stay `official-co` and
# unflagged here, and carry the government-voice conflict flag instead.
PARTISAN_DOMAINS = {
    # parties
    "centrodemocratico.com",
    "partidoliberal.org.co",
    "partidoconservador.com",
    "partidodelau.com",
    "cambioradical.org",
    "polodemocratico.net",
    "partidoverde.org.co",
    "colombiahumana.co",
    "pactohistorico.co",
    "partidomira.com",
    "partidofarc.com.co",
    "comunes.com.co",
    # campaigns and politicians' personal sites
    "ivanduque.com",
    "alvarouribevelez.com.co",
    "sergiofajardo.co",
    "fajardomoreno.com.co",
    "gustavopetro.co",
    "petro.com.co",
    "gustavopetroblog.wordpress.com",
}

# Executive voice: the government speaking about itself. Per DESIGN.md §5 the
# government is not a neutral primary source when the claim is *about the
# government*, so these are FLAGGED rather than retiered — they remain
# `official-co` (they are official publications, and D3 seeds its permissions
# audit from that tier), and the flag travels with them so retrieval can demand
# a counterweight (control bodies, courts, multilaterals, academia).
#
# Scope boundary: the presidency and vice-presidency families only. Ministries
# are executive too, but the corpus cites them mostly for technical data
# (epidemiology, statistics); widening the flag to them — or to state-owned
# companies beyond `interested-party` — is a judgment call left open.
GOVERNMENT_VOICE_DOMAINS = {
    "presidencia.gov.co",
    "vicepresidencia.gov.co",
}

REGISTRY_COLUMNS = [
    "domain",
    "tier",
    "role",
    "n_links",
    "n_articles",
    "scope_flag_partisan",
    "conflict_flag_government",
    "sample_urls",
]


def iter_article_files(cache_dir: Path) -> list[Path]:
    """List article pages in the cache, excluding listing pages.

    Args:
        cache_dir: Directory of cached HTML files.

    Returns:
        Sorted paths whose filename does not match the `*_page_<N>.html`
        listing pattern (1,000 of the 5,756 cached files are listings).
    """
    return sorted(p for p in cache_dir.glob("*.html") if not LISTING_RE.search(p.name))


def extract_verdict(soup: BeautifulSoup) -> str | None:
    """Read the verdict slug from the article wrapper's CSS classes.

    The wrapper `div.row.<verdict>.text-articulos` carries the verdict for all
    articles — including the 38% without JSON-LD. The `podcast` slug marks
    podcast episodes, not fact-checks.

    Args:
        soup: Parsed page.

    Returns:
        The verdict class token (e.g. `falso`), or None without a wrapper.
    """
    wrapper = soup.select_one("div.text-articulos")
    if wrapper is None:
        return None
    extra = [c for c in wrapper.get("class", []) if c not in {"row", "text-articulos"}]
    return extra[0] if extra else None


def select_body_container(soup: BeautifulSoup) -> Tag | None:
    """Locate the article-body (prose) container.

    The prose `<div>` has no id or class, so selection is positional: among
    the direct child `<div>`s of `div.col-12.col-md-9` — skipping the optional
    `#datos-claves` summary box — take the one with the most text.

    Args:
        soup: Parsed page.

    Returns:
        The prose Tag, or None when the page lacks the structure (listing
        pages, non-article layouts).
    """
    wrapper = soup.select_one("div.text-articulos")
    if wrapper is None:
        return None
    col = wrapper.select_one("div.col-12.col-md-9")
    if col is None:
        return None
    candidates = [
        d
        for d in col.find_all("div", recursive=False)
        if d.get("id") != "datos-claves"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda d: len(d.get_text()))


def extract_links(container: Tag) -> list[str]:
    """Collect cited URLs inside the prose container.

    Share/contact residue is dropped by URL pattern only; relative hrefs
    resolve against colombiacheck.com; non-HTTP schemes are discarded.

    Args:
        container: The prose Tag from `select_body_container`.

    Returns:
        Absolute URLs in document order (duplicates preserved).
    """
    links: list[str] = []
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        if any(pat in href for pat in RESIDUE_PATTERNS):
            continue
        url = urljoin(BASE_URL, href)
        if urlparse(url).scheme not in {"http", "https"}:
            continue
        links.append(url)
    return links


def domain_of(url: str) -> str:
    """Normalize a URL to its host: lowercase, no `www.`, no port.

    Args:
        url: Absolute URL.

    Returns:
        The normalized host, e.g. `dane.gov.co` for
        `https://WWW.Dane.GOV.co/x`. Subdomains other than `www` are kept.
    """
    netloc = urlparse(url).netloc.lower()
    netloc = netloc.rsplit("@", 1)[-1].split(":", 1)[0]
    return netloc.removeprefix("www.")


def _matches(domain: str, known: set[str]) -> bool:
    """True when the domain is in the set, or is a subdomain of a member.

    Subdomains matter throughout the corpus: `espanol.cdc.gov`,
    `co.linkedin.com` and `news.un.org` must inherit their parent's
    classification.

    Args:
        domain: Normalized host from `domain_of`.
        known: Curated domain set.

    Returns:
        Whether the domain belongs to the set's family.
    """
    return domain in known or any(domain.endswith("." + d) for d in known)


def classify_role(domain: str) -> str:
    """Classify a cited domain's role in a fact-check.

    Args:
        domain: Normalized host from `domain_of`.

    Returns:
        One of:
            `internal`: ColombiaCheck self-links (cross-references).
            `archive`: snapshot services (~17% of in-body links; short forms
                hide the true source and are offline-unresolvable).
            `claim-source`: social platforms — usually the claim under review.
            `tool`: search, media forensics and file hosting — the checker's
                method, not a source.
            `evidence`: everything else.
    """
    if _matches(domain, {"colombiacheck.com"}):
        return "internal"
    if _matches(domain, ARCHIVE_DOMAINS):
        return "archive"
    if _matches(domain, SOCIAL_DOMAINS):
        return "claim-source"
    if _matches(domain, PLATFORM_DOMAINS):
        return "tool"
    return "evidence"


def infer_tier(domain: str, role: str) -> str:
    """Infer a coarse source tier for a domain.

    Suffix rules plus curated sets; deliberately conservative — anything
    unknown lands in `other`, which means "needs human judgment", and is
    corrected through the overrides file rather than by guessing here.

    Args:
        domain: Normalized host.
        role: Output of `classify_role` for the same host.

    Returns:
        One of: `fact-checker`, `archive`, `social`, `platform`,
        `official-co`, `intl-org`, `academic`, `press`, `other`.
    """
    if role == "internal":
        return "fact-checker"
    if role == "archive":
        return "archive"
    if role == "claim-source":
        return "social"
    if role == "tool":
        return "platform"
    if domain.endswith((".gov.co", ".mil.co")):
        return "official-co"
    # Academic before intl-org: `pubmed.ncbi.nlm.nih.gov` is literature, while
    # `nih.gov` itself is a foreign official body.
    if _matches(domain, ACADEMIC_DOMAINS) or domain.endswith(
        (".edu", ".edu.co", ".ac.uk")
    ):
        return "academic"
    if _matches(domain, INTL_ORG_DOMAINS) or domain.endswith(".int"):
        return "intl-org"
    if _matches(domain, FACTCHECKER_DOMAINS):
        return "fact-checker"
    if _matches(domain, PRESS_DOMAINS):
        return "press"
    return "other"


def is_partisan(domain: str) -> bool:
    """Flag partisan-political domains (parties, campaigns, politicians).

    Args:
        domain: Normalized host.

    Returns:
        True when the domain (or a parent) is in the partisan list. The
        registry FLAGS rather than drops these, for auditability; the scope
        filter is applied downstream.
    """
    return _matches(domain, PARTISAN_DOMAINS)


def has_government_conflict(domain: str) -> bool:
    """Flag official sources that are the government's own voice.

    Args:
        domain: Normalized host.

    Returns:
        True for the presidency / vice-presidency families (all administration
        subdomains included). These stay `official-co`; the flag records the
        structural conflict of interest described in DESIGN.md §5, so that a
        claim *about the government* is not resolved with the government as
        its only primary source.
    """
    return _matches(domain, GOVERNMENT_VOICE_DOMAINS)


def apply_overrides(df: pd.DataFrame, overrides_path: Path) -> pd.DataFrame:
    """Apply manual corrections from the overrides CSV, if present.

    The overrides file (`domain,tier_override,scope_flag_override,reason`) is
    the only sanctioned way to correct the generated registry — never edit the
    output CSV, or the re-run-reproduces-the-committed-file guarantee dies.

    Args:
        df: Generated registry frame.
        overrides_path: Path to the overrides CSV; silently skipped if absent.

    Returns:
        The corrected frame (same rows, possibly changed `tier` /
        `scope_flag_partisan`).
    """
    if not overrides_path.exists():
        return df
    ov = pd.read_csv(overrides_path).set_index("domain")
    df = df.set_index("domain")
    for src, dst in (
        ("tier_override", "tier"),
        ("scope_flag_override", "scope_flag_partisan"),
        ("conflict_flag_override", "conflict_flag_government"),
    ):
        if src in ov.columns:
            vals = ov[src].dropna()
            hits = df.index.intersection(vals.index)
            df.loc[hits, dst] = vals.loc[hits]
    return df.reset_index()


def build_registry(
    cache_dir: Path,
    overrides_path: Path,
    limit: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build the domain registry from the cached corpus.

    Args:
        cache_dir: Cache directory of HTML pages.
        overrides_path: Manual-corrections CSV (may not exist).
        limit: Parse only the first N article files (smoke runs).

    Returns:
        A `(frame, stats)` pair: the registry sorted by `(-n_links, domain)`
        with `REGISTRY_COLUMNS`, and a stats dict with `n_files`, `n_parsed`,
        `n_container_missing` and the `missing` filenames.
    """
    files = iter_article_files(cache_dir)
    if limit is not None:
        files = files[:limit]
    agg: dict[str, dict] = {}
    missing: list[str] = []
    for path in files:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
        container = select_body_container(soup)
        if container is None:
            missing.append(path.name)
            continue
        for url in extract_links(container):
            domain = domain_of(url)
            if not domain:
                continue
            entry = agg.setdefault(
                domain, {"n_links": 0, "articles": set(), "urls": set()}
            )
            entry["n_links"] += 1
            entry["articles"].add(path.name)
            entry["urls"].add(url)
    rows = []
    for domain in sorted(agg):
        entry = agg[domain]
        role = classify_role(domain)
        rows.append(
            {
                "domain": domain,
                "tier": infer_tier(domain, role),
                "role": role,
                "n_links": entry["n_links"],
                "n_articles": len(entry["articles"]),
                "scope_flag_partisan": is_partisan(domain),
                "conflict_flag_government": has_government_conflict(domain),
                "sample_urls": "|".join(sorted(entry["urls"])[:3]),
            }
        )
    df = pd.DataFrame(rows, columns=REGISTRY_COLUMNS)
    df = apply_overrides(df, overrides_path)
    df = df.sort_values(
        ["n_links", "domain"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
    stats = {
        "n_files": len(files),
        "n_parsed": len(files) - len(missing),
        "n_container_missing": len(missing),
        "missing": missing,
    }
    return df, stats


def write_registry(df: pd.DataFrame, out_path: Path) -> None:
    """Write the registry CSV deterministically (sorted rows, LF, no index).

    Args:
        df: Registry frame from `build_registry`.
        out_path: Destination CSV path; parent directories are created.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, lineterminator="\n")


def main(argv: list[str] | None = None) -> None:
    """Build the registry from the CLI and print stats plus the top rows.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]`).
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache-dir", type=Path, default=paths.CACHE_COLOMBIACHECK)
    ap.add_argument("--out", type=Path, default=paths.REGISTRY_CSV)
    ap.add_argument("--overrides", type=Path, default=paths.REGISTRY_OVERRIDES)
    ap.add_argument("--limit", type=int, default=None, help="smoke run: first N files")
    ap.add_argument("--top", type=int, default=20, help="rows to print")
    args = ap.parse_args(argv)

    df, stats = build_registry(args.cache_dir, args.overrides, args.limit)
    write_registry(df, args.out)

    print(
        f"files: {stats['n_files']}  parsed: {stats['n_parsed']}  "
        f"container missing: {stats['n_container_missing']}"
    )
    for name in stats["missing"][:10]:
        print(f"  missing container: {name}")
    if args.limit is None and stats["n_parsed"] != 4756:
        print(f"WARNING: expected 4,756 parsed articles, got {stats['n_parsed']}")
    print(f"domains: {len(df)}  links: {int(df['n_links'].sum())}")
    print(f"wrote {args.out}")
    print(df.drop(columns=["sample_urls"]).head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()
