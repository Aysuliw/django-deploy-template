"""Send ERROR logs to a Telegram chat. Small teams read Telegram faster than email.

Never lets a failed alert break the request that logged the error, and sends the
same message at most once per COOLDOWN seconds, so one broken page during a traffic
spike doesn't flood the chat.
"""
import logging
import threading
import time

import requests
from django.conf import settings

COOLDOWN = 300
MAX_CHARS = 3500  # Telegram's limit is 4096


class TelegramHandler(logging.Handler):
    def __init__(self, level=logging.ERROR, clock=time.monotonic):
        super().__init__(level)
        self._clock = clock
        self._last_sent = {}
        self._lock = threading.Lock()

    def _should_send(self, key):
        now = self._clock()
        with self._lock:
            last = self._last_sent.get(key)
            if last is not None and now - last < COOLDOWN:
                return False
            self._last_sent[key] = now
            return True

    def emit(self, record):
        token, chat = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID
        if not token or not chat:
            return
        if not self._should_send((record.name, record.getMessage()[:200])):
            return
        try:
            text = f"🔴 {record.levelname} {record.name}\n{self.format(record)}"[:MAX_CHARS]
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": text},
                timeout=5,
            )
        except Exception:  # noqa: BLE001 - an alert must never raise
            self.handleError(record)
