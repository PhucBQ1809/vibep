from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from .config import AppConfig, TopicConfig
from .formatter import format_digest
from .models import Article
from .ranking import select_articles
from .sources import fetch_source
from .state import SentStore
from .telegram import send_messages

log = logging.getLogger(__name__)


def collect(topic: TopicConfig, config: AppConfig) -> list[Article]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda s: fetch_source(s, config), topic.sources)
    return [a for batch in results for a in batch]


def run_topic(topic: TopicConfig, config: AppConfig, store: SentStore, dry_run: bool) -> int:
    """Build and deliver one topic's digest. Returns the number of articles sent."""
    log.info("== Topic %s ==", topic.id)
    articles = collect(topic, config)
    weights = {s.name: s.weight for s in topic.sources}
    picked = select_articles(articles, topic, store.sent_ids(topic.id), weights)
    log.info("Fetched %d, selected %d", len(articles), len(picked))

    if not picked:
        log.info("Nothing new for %s", topic.id)
        return 0

    messages = format_digest(topic, picked)
    if dry_run:
        for m in messages:
            print(m, end="\n\n" + "-" * 40 + "\n\n")
        return len(picked)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or not topic.chat_id:
        raise RuntimeError(
            f"Missing TELEGRAM_BOT_TOKEN or {topic.chat_id_env} for topic '{topic.id}'"
        )
    send_messages(token, topic.chat_id, messages)
    store.mark_sent(topic.id, [a.uid for a in picked])
    return len(picked)
