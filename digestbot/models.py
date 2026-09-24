from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query params that only track the click and don't change the article.
_TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "igshid", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    """Canonical form of a URL so the same article isn't sent twice."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None = None
    summary: str = ""
    score: float = 0.0
    tags: list[str] = field(default_factory=list)
    meta: str = ""  # extra info shown next to the source, e.g. upvotes

    @property
    def uid(self) -> str:
        return hashlib.sha1(normalize_url(self.url).encode("utf-8")).hexdigest()[:16]
