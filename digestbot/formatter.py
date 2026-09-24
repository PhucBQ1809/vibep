from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from .config import TopicConfig
from .models import Article

TELEGRAM_LIMIT = 4096
VN_TZ = timezone(timedelta(hours=7))


def _format_item(index: int, a: Article, show_summary: bool) -> str:
    lines = [f'<b>{index}. <a href="{escape(a.url, quote=True)}">{escape(a.title)}</a></b>']
    if show_summary and a.summary and a.summary.lower() != a.title.lower():
        lines.append(f"<i>{escape(a.summary)}</i>")
    footer = f"🔗 {escape(a.source)}"
    if a.meta:
        footer += f" · {escape(a.meta)}"
    lines.append(footer)
    return "\n".join(lines)


def format_digest(
    topic: TopicConfig,
    articles: list[Article],
    now: datetime | None = None,
    show_summary: bool = True,
) -> list[str]:
    """Build Telegram HTML messages, split so each stays under the size limit."""
    now = (now or datetime.now(timezone.utc)).astimezone(VN_TZ)
    header = (
        f"{topic.emoji} <b>{escape(topic.title)}</b> — {now:%d/%m/%Y}\n"
        f"Tổng hợp {len(articles)} bài viết đáng đọc\n"
    )
    messages: list[str] = []
    current = header
    for i, a in enumerate(articles, 1):
        block = "\n" + _format_item(i, a, show_summary) + "\n"
        if len(current) + len(block) > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = block.lstrip("\n")
        else:
            current += block
    messages.append(current.rstrip())
    return messages
