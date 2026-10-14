#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отправка готового видео в Telegram."""
import os
import sys
from pathlib import Path

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

VIDEO = Path("output.mp4")
TOPIC_FILE = Path("current_topic.txt")


def log(msg: str):
    print(f"[TG] {msg}", flush=True)


def send_video():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы — пропускаем отправку")
        return

    if not VIDEO.exists():
        log("Файл output.mp4 не найден")
        return

    topic = TOPIC_FILE.read_text(encoding="utf-8").strip() if TOPIC_FILE.exists() else "Фасадные панели"
    caption = f"🎥 {topic}\n\n#фасадныепанели #строительство #контентзавод"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(VIDEO, "rb") as f:
        files = {"video": f}
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "supports_streaming": True,
        }
        log(f"Отправка видео в чат {TELEGRAM_CHAT_ID}...")
        resp = requests.post(url, data=data, files=files, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        if result.get("ok"):
            log("Видео успешно отправлено в Telegram")
        else:
            log(f"Ошибка Telegram: {result}")
            raise RuntimeError(result)


if __name__ == "__main__":
    try:
        send_video()
    except Exception as e:
        log(f"Ошибка отправки: {e}")
        sys.exit(1)
