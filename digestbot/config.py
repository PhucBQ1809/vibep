from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SourceConfig:
    name: str
    url: str
    type: str = "rss"
    weight: float = 1.0
    # reddit only: skip posts with fewer upvotes / comments than this
    min_score: int = 0
    min_comments: int = 0


@dataclass
class TopicConfig:
    id: str
    title: str
    sources: list[SourceConfig]
    enabled: bool = True
    emoji: str = "📰"
    # Name of the env var holding the Telegram chat id for this topic.
    chat_id_env: str = "TELEGRAM_CHAT_ID"
    max_items: int = 10
    max_age_hours: int = 36
    max_per_source: int = 3
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    boost_keywords: list[str] = field(default_factory=list)

    @property
    def chat_id(self) -> str | None:
        return os.environ.get(self.chat_id_env) or None


@dataclass
class AppConfig:
    topics: list[TopicConfig]
    user_agent: str = "Mozilla/5.0 (compatible; digestbot/1.0)"
    request_timeout: int = 20

    def topic(self, topic_id: str) -> TopicConfig:
        for t in self.topics:
            if t.id == topic_id:
                return t
        raise KeyError(f"Unknown topic '{topic_id}'. Available: {[t.id for t in self.topics]}")


def _lower(words: list[str] | None) -> list[str]:
    return [unicodedata.normalize("NFC", w).lower() for w in (words or [])]


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    settings = raw.get("settings", {}) or {}
    topics = []
    for topic_id, t in (raw.get("topics") or {}).items():
        sources = [SourceConfig(**s) for s in t.get("sources", [])]
        if not sources:
            raise ValueError(f"Topic '{topic_id}' has no sources")
        topics.append(
            TopicConfig(
                id=topic_id,
                title=t.get("title", topic_id),
                sources=sources,
                enabled=t.get("enabled", True),
                emoji=t.get("emoji", "📰"),
                chat_id_env=t.get("chat_id_env", "TELEGRAM_CHAT_ID"),
                max_items=t.get("max_items", 10),
                max_age_hours=t.get("max_age_hours", 36),
                max_per_source=t.get("max_per_source", 3),
                include_keywords=_lower(t.get("include_keywords")),
                exclude_keywords=_lower(t.get("exclude_keywords")),
                boost_keywords=_lower(t.get("boost_keywords")),
            )
        )
    return AppConfig(
        topics=topics,
        user_agent=settings.get("user_agent", AppConfig.user_agent),
        request_timeout=settings.get("request_timeout", AppConfig.request_timeout),
    )
