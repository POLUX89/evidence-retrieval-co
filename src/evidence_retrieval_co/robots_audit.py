"""robots.txt audit for the permissions table (DESIGN.md §6).

Step 1 of ingestion is not writing a collector: it is auditing what each domain
permits. This module fetches **only** `/robots.txt` — never article content —
and turns each file into the columns the audit table needs: which AI crawlers
the site blocks, whether it disallows everything, and any declared sitemap or
feed.

Two things this deliberately does NOT do:

- Decide anything. robots.txt is the floor; the Terms of Service weigh more and
  need human reading. A domain is never marked green from here.
- Assume absence of a block means permission. It only records what the file
  says, so `docs/PERMISSIONS.md` can show the evidence behind each verdict.

Results are a dated snapshot, not a reproducible derivation: policies change,
which is exactly why the table carries a review date.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from evidence_retrieval_co import paths
from evidence_retrieval_co.colombiacheck import get

# Crawlers to look for on every domain (DESIGN.md §6), plus the ones that have
# become common since the design doc was written.
AI_USER_AGENTS = (
    "Google-Extended",
    "GPTBot",
    "ChatGPT-User",
    "CCBot",
    "ClaudeBot",
    "anthropic-ai",
    "PerplexityBot",
    "Applebot-Extended",
    "Bytespider",
    "meta-externalagent",
)

AUDIT_COLUMNS = [
    "domain",
    "entity",
    "tier",
    "robots_found",
    "wildcard_verdict",
    "ai_agents_blocked",
    "has_ai_clause",
    "feed_hint",
    "checked_date",
]


def parse_robots(text: str) -> dict:
    """Parse a robots.txt into per-user-agent rule groups.

    Consecutive `User-agent` lines share the rules that follow them, per RFC
    9309. Comments and malformed lines are skipped.

    Args:
        text: Raw robots.txt content.

    Returns:
        Dict with `groups` (lowercased agent -> list of `(field, value)`) and
        `sitemaps` (declared sitemap URLs).
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    sitemaps: list[str] = []
    current: list[str] = []
    in_rules = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if in_rules:
                current = []
                in_rules = False
            agent = value.lower()
            current.append(agent)
            groups.setdefault(agent, [])
        elif field in {"disallow", "allow"}:
            in_rules = True
            for agent in current:
                groups[agent].append((field, value))
        elif field == "sitemap" and value:
            sitemaps.append(value)
    return {"groups": groups, "sitemaps": sitemaps}


def agent_verdict(groups: dict[str, list[tuple[str, str]]], agent: str) -> str:
    """Summarize what a robots.txt grants one user-agent.

    Args:
        groups: The `groups` mapping from `parse_robots`.
        agent: User-agent token to look up (case-insensitive).

    Returns:
        `blocked` (Disallow: /), `partial` (some paths disallowed), `allowed`
        (a group exists but forbids nothing) or `not mentioned`.
    """
    rules = groups.get(agent.lower())
    if rules is None:
        return "not mentioned"
    if any(field == "disallow" and value == "/" for field, value in rules):
        return "blocked"
    if any(field == "disallow" and value for field, value in rules):
        return "partial"
    return "allowed"


def feed_hint(parsed: dict) -> str:
    """Report any feed-looking URL the robots.txt declares.

    Args:
        parsed: Output of `parse_robots`.

    Returns:
        The first sitemap or rule path mentioning rss/feed/atom, else an empty
        string. A hint only — the real feed check belongs to the audit.
    """
    for url in parsed["sitemaps"]:
        if any(token in url.lower() for token in ("rss", "feed", "atom")):
            return url
    for rules in parsed["groups"].values():
        for _, value in rules:
            if any(token in value.lower() for token in ("rss", "feed", "atom")):
                return value
    return parsed["sitemaps"][0] if parsed["sitemaps"] else ""


def audit_domain(
    domain: str,
    session: requests.Session,
    cache_dir: Path,
    checked: str,
) -> dict:
    """Fetch and summarize one domain's robots.txt.

    Args:
        domain: Host to audit (no scheme).
        session: Shared `requests.Session`.
        cache_dir: Where fetched robots.txt files are cached.
        checked: ISO date recorded as the review date.

    Returns:
        A row keyed by `AUDIT_COLUMNS` (minus `entity` and `tier`, which the
        caller joins in).
    """
    text = get(
        f"https://{domain}/robots.txt",
        session,
        cache_dir=cache_dir,
        suffix=".txt",
        timeout=10,
        retries=2,
    )
    if text is None:
        return {
            "domain": domain,
            "robots_found": False,
            "wildcard_verdict": "",
            "ai_agents_blocked": "",
            "has_ai_clause": False,
            "feed_hint": "",
            "checked_date": checked,
        }
    parsed = parse_robots(text)
    blocked = [
        agent
        for agent in AI_USER_AGENTS
        if agent_verdict(parsed["groups"], agent) in {"blocked", "partial"}
    ]
    return {
        "domain": domain,
        "robots_found": True,
        "wildcard_verdict": agent_verdict(parsed["groups"], "*"),
        "ai_agents_blocked": "|".join(blocked),
        "has_ai_clause": bool(blocked),
        "feed_hint": feed_hint(parsed),
        "checked_date": checked,
    }


def audit(
    targets: pd.DataFrame,
    cache_dir: Path = paths.DATA_CACHE / "robots",
    checked: str | None = None,
) -> pd.DataFrame:
    """Audit every target domain's robots.txt.

    Args:
        targets: Frame with at least `domain`; `entity` and `tier` are carried
            through when present.
        cache_dir: Cache for the fetched files (git-ignored).
        checked: ISO review date; defaults to today (UTC).

    Returns:
        One row per domain, ordered by `AUDIT_COLUMNS`.
    """
    checked = checked or datetime.now(tz=UTC).date().isoformat()
    session = requests.Session()
    rows = []
    for i, target in enumerate(targets.itertuples(index=False), start=1):
        row = audit_domain(target.domain, session, cache_dir, checked)
        row["entity"] = getattr(target, "entity", "")
        row["tier"] = getattr(target, "tier", "")
        rows.append(row)
        flag = "AI clause" if row["has_ai_clause"] else ""
        found = "ok" if row["robots_found"] else "no robots.txt"
        print(f"[{i}/{len(targets)}] {target.domain}: {found} {flag}".rstrip())
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def main(argv: list[str] | None = None) -> None:
    """Audit the domains listed in a CSV and write the results.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]`).
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", type=Path, required=True, help="CSV with a domain column")
    ap.add_argument("--out", type=Path, default=paths.DATA_REGISTRY / "robots_audit.csv")
    ap.add_argument("--cache-dir", type=Path, default=paths.DATA_CACHE / "robots")
    ap.add_argument("--checked", default=None, help="ISO review date (default: today)")
    args = ap.parse_args(argv)

    targets = pd.read_csv(args.targets)
    result = audit(targets, args.cache_dir, args.checked)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False, lineterminator="\n")
    print(f"\nwrote {args.out}")
    print(f"robots.txt found: {int(result.robots_found.sum())}/{len(result)}")
    print(f"with an AI clause: {int(result.has_ai_clause.sum())}")


if __name__ == "__main__":
    main()
