from datetime import datetime, timezone
from pathlib import Path

import pytest

from digestbot.config import SourceConfig, TopicConfig, load_config
from digestbot.formatter import TELEGRAM_LIMIT, format_digest
from digestbot.models import Article, normalize_url
from digestbot.ranking import select_articles
from digestbot.sources import parse_feed
from digestbot.state import SentStore

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)
SOURCE = SourceConfig(name="Sample", url="https://example.com/feed")


def make_topic(**kw) -> TopicConfig:
    defaults = dict(id="mmo", title="MMO", sources=[SOURCE])
    defaults.update(kw)
    return TopicConfig(**defaults)


@pytest.fixture
def articles():
    return parse_feed((ROOT / "tests/fixtures/sample_feed.xml").read_bytes(), SOURCE)


def test_parse_feed_cleans_html(articles):
    assert len(articles) == 4
    assert articles[0].summary == "How we grew a niche site with SEO."
    assert articles[0].published == datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)


def test_normalize_url_strips_tracking():
    assert normalize_url("https://Example.com/a/?utm_source=x&id=1") == "https://example.com/a?id=1"


def test_select_filters_age_and_keywords(articles):
    topic = make_topic(exclude_keywords=["casino"], boost_keywords=["affiliate", "niche"])
    picked = select_articles(articles, topic, set(), {}, now=NOW)
    titles = [a.title for a in picked]
    assert "Best online casino bonuses" not in titles
    assert "Old post about blogging" not in titles
    assert titles[0].startswith("Case study")  # boosted to the top
    assert len(picked) == 2


def test_select_skips_already_sent(articles):
    topic = make_topic()
    sent = {articles[0].uid}
    picked = select_articles(articles, topic, sent, {}, now=NOW)
    assert all(a.uid != articles[0].uid for a in picked)


def test_keywords_match_whole_words_only():
    a = Article(title="He said hello", url="https://x.com/1", source="S", published=NOW)
    b = Article(title="New AI tool", url="https://x.com/2", source="S", published=NOW)
    picked = select_articles([a, b], make_topic(include_keywords=["ai"]), set(), {}, now=NOW)
    assert [p.title for p in picked] == ["New AI tool"]


def test_vietnamese_keywords(articles):
    topic = make_topic(include_keywords=["tiktok shop"], max_age_hours=48)
    picked = select_articles(articles, topic, set(), {}, now=NOW)
    assert [a.url for a in picked] == ["https://example.com/tiktok-shop"]


def test_max_per_source_and_dedupe():
    items = [
        Article(title=f"Post {i}", url=f"https://x.com/{i}", source="A", published=NOW)
        for i in range(5)
    ] + [Article(title="Post 0", url="https://y.com/dup", source="B", published=NOW)]
    picked = select_articles(items, make_topic(max_per_source=2), set(), {}, now=NOW)
    assert len(picked) == 2


def test_format_splits_long_digest():
    items = [
        Article(title="T" * 190, url=f"https://x.com/{i}", source="S", summary="s" * 290)
        for i in range(40)
    ]
    messages = format_digest(make_topic(), items, now=NOW)
    assert len(messages) > 1
    assert all(len(m) <= TELEGRAM_LIMIT for m in messages)
    assert messages[0].startswith("📰 <b>MMO</b> — 24/09/2026")


def test_format_escapes_html():
    a = Article(title="A <b> & B", url="https://x.com/?a=1&b=2", source="S")
    text = format_digest(make_topic(), [a], now=NOW)[0]
    assert "A &lt;b&gt; &amp; B" in text
    assert 'href="https://x.com/?a=1&amp;b=2"' in text


def test_state_roundtrip_and_prune(tmp_path):
    path = tmp_path / "sent.json"
    store = SentStore(path, retention_days=30)
    store.mark_sent("mmo", ["old"], now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    store.mark_sent("mmo", ["new"], now=NOW)
    store.prune(now=NOW)
    store.save()
    assert SentStore(path).sent_ids("mmo") == {"new"}


def test_repo_config_loads():
    config = load_config(ROOT / "config/topics.yaml")
    assert config.topic("mmo").enabled
    assert all(s.url.startswith("https://") for t in config.topics for s in t.sources)
