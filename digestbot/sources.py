"""Fetchers turning a configured source into a list of Articles.

To support a new kind of source (an API, a scraped page...), write a function
with the same signature as `fetch_rss` and register it in FETCHERS.
"""
from __future__ import annotations

import html
import logging
import re
from calendar import timegm
from datetime import datetime, timezone
from typing import Callable

import feedparser
import requests

from .config import AppConfig, SourceConfig
from .models import Article

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(text: str, limit: int = 300) -> str:
    text = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text or ""))).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(timegm(value), tz=timezone.utc)
    return None


def parse_feed(content: bytes | str, source: SourceConfig) -> list[Article]:
    feed = feedparser.parse(content)
    articles = []
    for entry in feed.entries:
        title = clean_text(entry.get("title", ""), limit=200)
        link = entry.get("link", "")
        if not title or not link:
            continue
        articles.append(
            Article(
                title=title,
                url=link,
                source=source.name,
                published=_entry_datetime(entry),
                summary=clean_text(entry.get("summary", "")),
                tags=[t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
            )
        )
    return articles


def fetch_rss(source: SourceConfig, config: AppConfig) -> list[Article]:
    resp = requests.get(
        source.url,
        headers={"User-Agent": config.user_agent},
        timeout=config.request_timeout,
    )
    resp.raise_for_status()
    return parse_feed(resp.content, source)


FETCHERS: dict[str, Callable[[SourceConfig, AppConfig], list[Article]]] = {
    "rss": fetch_rss,
}


def fetch_source(source: SourceConfig, config: AppConfig) -> list[Article]:
    fetcher = FETCHERS.get(source.type)
    if fetcher is None:
        log.error("Unknown source type '%s' for %s", source.type, source.name)
        return []
    try:
        articles = fetcher(source, config)
        log.info("%-30s %3d items", source.name, len(articles))
        return articles
    except Exception as exc:  # one broken feed must not kill the digest
        log.warning("Failed to fetch %s (%s): %s", source.name, source.url, exc)
        return []
