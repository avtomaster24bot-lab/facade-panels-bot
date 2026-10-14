#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отправка готового видео в Telegram (как в рабочем репозитории)."""
import os
import sys
import asyncio
from pathlib import Path

from telegram import Bot
from telegram.request import HTTPXRequest

VIDEO = Path("output.mp4")
TOPIC_FILE = Path("current_topic.txt")


def log(msg: str):
    print(f"[TG] {msg}", flush=True)


async def send():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    log(f"Token length: {len(token)}")
    log(f"Chat ID: '{chat_id}'")
    log(f"Video exists: {VIDEO.exists()}")

    if not token or not chat_id:
        log("TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы")
        return

    if not VIDEO.exists():
        log("Файл output.mp4 не найден")
        return

    topic = TOPIC_FILE.read_text(encoding="utf-8").strip() if TOPIC_FILE.exists() else "Фасадные панели"
    caption = f"🎥 {topic}\n\n#фасадныепанели #строительство #контентзавод"

    request = HTTPXRequest(connection_pool_size=1, read_timeout=120, write_timeout=120)
    bot = Bot(token=token, request=request)

    try:
        me = await bot.get_me()
        log(f"Bot OK: @{me.username}")

        with open(VIDEO, "rb") as f:
            await bot.send_video(
                chat_id=chat_id,
                video=f,
                caption=caption[:1024],
                supports_streaming=True,
            )
        log("Видео успешно отправлено")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(send())
    except Exception as e:
        log(f"Ошибка отправки: {e}")
        sys.exit(1)
