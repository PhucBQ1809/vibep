"""Remembers which articles were already sent, per topic, in a JSON file."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SentStore:
    def __init__(self, path: str | Path, retention_days: int = 30):
        self.path = Path(path)
        self.retention = timedelta(days=retention_days)
        self._data: dict[str, dict[str, str]] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8") or "{}")

    def sent_ids(self, topic_id: str) -> set[str]:
        return set(self._data.get(topic_id, {}))

    def mark_sent(self, topic_id: str, uids: list[str], now: datetime | None = None) -> None:
        stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
        bucket = self._data.setdefault(topic_id, {})
        for uid in uids:
            bucket[uid] = stamp

    def prune(self, now: datetime | None = None) -> None:
        cutoff = (now or datetime.now(timezone.utc)) - self.retention
        for topic_id, bucket in self._data.items():
            self._data[topic_id] = {
                uid: ts for uid, ts in bucket.items() if datetime.fromisoformat(ts) >= cutoff
            }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
