"""Source collector with a hard permissions gate (DESIGN.md §6).

The gate is the point of this module. Every source carries an `audit_status`
mirroring its row in `docs/PERMISSIONS.md`, and **nothing is fetched unless
that status is `green`**. The check runs inside the fetch path, not only in the
planner, so no caller can route around it.

Fail-closed and loud: an unknown or misspelled status is not treated as
permissive, it raises. A source with no feed URL is refused even when green.

The bootstrap ships with zero green sources, so a plain run fetches nothing —
which is the intended state until the per-domain audit (robots.txt **and**
Terms of Service) is complete.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml

from evidence_retrieval_co import paths

# `out-of-scope` records our own decision not to pursue a source, which is a
# different fact from the source refusing us (`red`) or from an unfinished
# review (`pending`). Conflating them would make the audit look like a wall of
# rejections when part of it is simply a narrowing of the project.
AUDIT_STATUSES = ("green", "amber", "red", "pending", "out-of-scope")
REQUIRED_FIELDS = ("name", "domain", "tier", "audit_status")


class PermissionGateError(RuntimeError):
    """Raised when collection is attempted on a source that is not cleared."""


@dataclass(frozen=True)
class Source:
    """One configured source and its audit state.

    Attributes:
        name: Human-readable name, as it appears in the permissions table.
        domain: Host the audit applies to.
        tier: Corpus tier (`official-co`, `press`, ...).
        audit_status: One of `AUDIT_STATUSES`; only `green` may be fetched.
        rss_url: Feed URL, or None while the feed is unknown or unapproved.
        notes: Free-text justification carried from the audit.
    """

    name: str
    domain: str
    tier: str
    audit_status: str
    rss_url: str | None = None
    notes: str = ""


def load_sources(path: Path = paths.SOURCES_YAML) -> list[Source]:
    """Read and validate the source configuration.

    Args:
        path: YAML file with a top-level `sources` list.

    Returns:
        The configured sources.

    Raises:
        ValueError: If an entry misses a required field or carries a status
            outside `AUDIT_STATUSES`. Validation is strict on purpose: a typo
            must never widen access silently.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("sources") or []
    sources = []
    for i, entry in enumerate(entries):
        missing = [f for f in REQUIRED_FIELDS if not entry.get(f)]
        if missing:
            raise ValueError(
                f"{path.name}: entry #{i} ({entry.get('name', 'unnamed')}) "
                f"is missing required field(s): {', '.join(missing)}"
            )
        if entry["audit_status"] not in AUDIT_STATUSES:
            raise ValueError(
                f"{path.name}: entry #{i} ({entry['name']}) has audit_status "
                f"{entry['audit_status']!r}; expected one of "
                f"{', '.join(AUDIT_STATUSES)}"
            )
        sources.append(
            Source(
                name=entry["name"],
                domain=entry["domain"],
                tier=entry["tier"],
                audit_status=entry["audit_status"],
                rss_url=entry.get("rss_url"),
                notes=entry.get("notes", ""),
            )
        )
    return sources


def assert_fetch_allowed(source: Source) -> None:
    """Enforce the permissions gate for one source.

    Args:
        source: The source about to be fetched.

    Raises:
        PermissionGateError: Unless `audit_status` is `green` and a feed URL is
            configured.
    """
    if source.audit_status == "out-of-scope":
        raise PermissionGateError(
            f"Refusing to fetch {source.name!r} ({source.domain}): the source is "
            f"out of scope by project decision, not by refusal. See "
            f"docs/PERMISSIONS.md."
        )
    if source.audit_status != "green":
        raise PermissionGateError(
            f"Refusing to fetch {source.name!r} ({source.domain}): audit_status "
            f"is {source.audit_status!r}, not 'green'. Complete the per-domain "
            f"audit in docs/PERMISSIONS.md before enabling collection."
        )
    if not source.rss_url:
        raise PermissionGateError(
            f"Refusing to fetch {source.name!r} ({source.domain}): cleared for "
            f"collection but no rss_url is configured."
        )


def fetch_source(source: Source, fetcher=None) -> object:
    """Fetch one source's feed, gate first.

    Args:
        source: The source to collect.
        fetcher: Callable taking the feed URL; injected in tests. Defaults to
            the feedparser-backed reader, imported lazily so the base install
            and CI never need the `collect` extra.

    Returns:
        Whatever the fetcher returns (a parsed feed).

    Raises:
        PermissionGateError: If the source is not cleared.
    """
    assert_fetch_allowed(source)
    if fetcher is None:
        fetcher = _default_fetcher
    return fetcher(source.rss_url)


def _default_fetcher(url: str) -> object:
    """Read one feed with feedparser (lazy import).

    Args:
        url: Feed URL.

    Returns:
        The parsed feed object.
    """
    # Imported here rather than at module scope so the `collect` extra stays
    # optional: the base install, CI and every dry run work without it.
    import feedparser

    return feedparser.parse(url)


def plan(sources: list[Source]) -> tuple[list[Source], list[tuple[Source, str]]]:
    """Split sources into fetchable and refused, without fetching.

    Args:
        sources: Configured sources.

    Returns:
        `(allowed, refused)` where each refused entry pairs the source with the
        gate's reason.
    """
    allowed, refused = [], []
    for source in sources:
        try:
            assert_fetch_allowed(source)
        except PermissionGateError as exc:
            refused.append((source, str(exc)))
        else:
            allowed.append(source)
    return allowed, refused


def main(argv: list[str] | None = None) -> int:
    """Report what would be collected, or collect what is cleared.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]`).

    Returns:
        Process exit code (0 — refusing everything is a valid outcome, not an
        error).
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=paths.SOURCES_YAML)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be fetched and exit without any network access",
    )
    args = ap.parse_args(argv)

    sources = load_sources(args.config)
    allowed, refused = plan(sources)

    for source in allowed:
        print(f"WOULD FETCH  {source.name} ({source.domain}) -> {source.rss_url}")
    for source, reason in refused:
        print(f"REFUSED      {source.name} ({source.domain}): {reason.split(': ', 1)[1]}")
    print(f"\n{len(allowed)} of {len(sources)} sources eligible.")

    if args.dry_run:
        print("Dry run: no network access performed.")
        return 0
    if not allowed:
        print("Nothing to fetch.")
        return 0
    for source in allowed:
        print(f"fetching {source.name} ...")
        fetch_source(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
