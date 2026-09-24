from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from .config import TopicConfig
from .models import Article, normalize_url


def _haystack(article: Article) -> str:
    text = " ".join([article.title, article.summary, " ".join(article.tags)])
    # Vietnamese feeds sometimes use decomposed accents; compare in NFC form.
    return unicodedata.normalize("NFC", text).lower()


@lru_cache(maxsize=None)
def _keyword_re(keyword: str) -> re.Pattern[str]:
    # Whole-word match so "ai" doesn't hit "said"; works for Vietnamese too.
    return re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)")


def _has(text: str, keyword: str) -> bool:
    return _keyword_re(keyword).search(text) is not None


def _normalize_title(title: str) -> str:
    return "".join(ch for ch in title.lower() if ch.isalnum())


def select_articles(
    articles: list[Article],
    topic: TopicConfig,
    sent_ids: set[str],
    source_weights: dict[str, float],
    now: datetime | None = None,
) -> list[Article]:
    """Filter, dedupe, score and pick the best articles for one digest."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=topic.max_age_hours)

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    candidates: list[Article] = []

    for a in articles:
        if a.uid in sent_ids:
            continue
        url_key, title_key = normalize_url(a.url), _normalize_title(a.title)
        if url_key in seen_urls or title_key in seen_titles:
            continue
        if a.published and a.published < cutoff:
            continue

        text = _haystack(a)
        if topic.exclude_keywords and any(_has(text, k) for k in topic.exclude_keywords):
            continue
        if topic.include_keywords and not any(_has(text, k) for k in topic.include_keywords):
            continue

        seen_urls.add(url_key)
        seen_titles.add(title_key)

        boost = sum(1 for k in topic.boost_keywords if _has(text, k))
        if a.published:
            age_h = max((now - a.published).total_seconds() / 3600, 0)
            freshness = max(0.0, 1 - age_h / topic.max_age_hours)
        else:
            freshness = 0.3
        a.score = source_weights.get(a.source, 1.0) * (1 + 0.5 * boost + freshness)
        candidates.append(a)

    candidates.sort(key=lambda a: a.score, reverse=True)

    picked: list[Article] = []
    per_source: Counter[str] = Counter()
    for a in candidates:
        if per_source[a.source] >= topic.max_per_source:
            continue
        per_source[a.source] += 1
        picked.append(a)
        if len(picked) >= topic.max_items:
            break
    return picked
