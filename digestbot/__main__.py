"""CLI: python -m digestbot [--topic mmo] [--dry-run]"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .pipeline import run_topic
from .state import SentStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="digestbot", description=__doc__)
    parser.add_argument("--config", default="config/topics.yaml")
    parser.add_argument("--state", default="data/sent.json")
    parser.add_argument(
        "--topic",
        action="append",
        help="Topic id to run (repeatable). Default: all enabled topics.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print instead of sending")
    parser.add_argument("--list", action="store_true", help="List topics and exit")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)

    if args.list:
        for t in config.topics:
            status = "on " if t.enabled else "off"
            print(f"[{status}] {t.id:<12} {t.title} ({len(t.sources)} sources)")
        return 0

    topics = [config.topic(t) for t in args.topic] if args.topic else [
        t for t in config.topics if t.enabled
    ]

    store = SentStore(args.state)
    failed = []
    for topic in topics:
        try:
            run_topic(topic, config, store, args.dry_run)
        except Exception:
            logging.exception("Topic %s failed", topic.id)
            failed.append(topic.id)

    if not args.dry_run:
        store.prune()
        store.save()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
