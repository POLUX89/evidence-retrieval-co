"""robots.txt parsing and verdicts. No network: all fixtures are synthetic."""

from evidence_retrieval_co import robots_audit as ra

ROBOTS = """
# Synthetic robots.txt for tests
User-agent: *
Disallow: /wp-admin/
Allow: /

User-agent: GPTBot
User-agent: ChatGPT-User
Disallow: /

User-agent: Google-Extended
Disallow:

Sitemap: https://example.test/sitemap.xml
Sitemap: https://example.test/rss/news.xml
"""


def test_consecutive_user_agents_share_the_following_rules():
    groups = ra.parse_robots(ROBOTS)["groups"]
    assert groups["gptbot"] == [("disallow", "/")]
    assert groups["chatgpt-user"] == [("disallow", "/")]


def test_verdicts():
    groups = ra.parse_robots(ROBOTS)["groups"]
    assert ra.agent_verdict(groups, "GPTBot") == "blocked"
    assert ra.agent_verdict(groups, "ChatGPT-User") == "blocked"
    assert ra.agent_verdict(groups, "*") == "partial"
    # An empty Disallow forbids nothing — it is not a block.
    assert ra.agent_verdict(groups, "Google-Extended") == "allowed"
    assert ra.agent_verdict(groups, "ClaudeBot") == "not mentioned"


def test_agent_lookup_is_case_insensitive():
    groups = ra.parse_robots("User-agent: CCBot\nDisallow: /")["groups"]
    assert ra.agent_verdict(groups, "ccbot") == "blocked"
    assert ra.agent_verdict(groups, "CCBot") == "blocked"


def test_comments_and_junk_lines_ignored():
    parsed = ra.parse_robots("# just a comment\nnot a directive\nUser-agent: *\nDisallow: /x")
    assert parsed["groups"] == {"*": [("disallow", "/x")]}
    assert parsed["sitemaps"] == []


def test_feed_hint_prefers_a_feed_looking_sitemap():
    assert ra.feed_hint(ra.parse_robots(ROBOTS)) == "https://example.test/rss/news.xml"


def test_feed_hint_empty_without_sitemaps():
    assert ra.feed_hint(ra.parse_robots("User-agent: *\nDisallow:")) == ""


def test_audit_domain_uses_cache_and_flags_ai_clause(tmp_path):
    from evidence_retrieval_co.colombiacheck import cache_key

    url = "https://example.test/robots.txt"
    (tmp_path / cache_key(url, ".txt")).write_text(ROBOTS)
    # A session without .get() would raise if the network path were touched.
    row = ra.audit_domain("example.test", object(), tmp_path, "2026-08-14")
    assert row["robots_found"] is True
    assert row["has_ai_clause"] is True
    assert "GPTBot" in row["ai_agents_blocked"]
    assert row["checked_date"] == "2026-08-14"


def test_audit_domain_records_a_missing_robots(tmp_path, monkeypatch):
    monkeypatch.setattr(ra, "get", lambda *a, **k: None)
    row = ra.audit_domain("nowhere.test", object(), tmp_path, "2026-08-14")
    assert row["robots_found"] is False
    assert row["has_ai_clause"] is False
    assert row["ai_agents_blocked"] == ""
