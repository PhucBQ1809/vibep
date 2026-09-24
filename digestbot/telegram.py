from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramError(RuntimeError):
    pass


def send_message(token: str, chat_id: str, text: str, retries: int = 3) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(1, retries + 1):
        resp = requests.post(API_URL.format(token=token), json=payload, timeout=20)
        if resp.ok:
            return
        if resp.status_code == 429:  # rate limited: Telegram says how long to wait
            wait = resp.json().get("parameters", {}).get("retry_after", 5)
            log.warning("Rate limited by Telegram, waiting %ss", wait)
            time.sleep(wait)
            continue
        if resp.status_code >= 500 and attempt < retries:
            time.sleep(2**attempt)
            continue
        raise TelegramError(f"Telegram API {resp.status_code}: {resp.text}")
    raise TelegramError("Telegram API: retries exhausted")


def send_messages(token: str, chat_id: str, messages: list[str]) -> None:
    for i, text in enumerate(messages):
        if i:
            time.sleep(1)
        send_message(token, chat_id, text)
