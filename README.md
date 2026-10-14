# Контент-завод «Фасадные панели»

Автономный пайплайн генерации коротких образовательных видео на тему фасадных панелей.

Каждый день (или по кнопке) бот:
1. Берёт следующую необработанную тему из `content_plan.json`
2. Генерирует сценарий через Gemini 1.5 Flash
3. Подбирает фото на Pexels
4. Накладывает текст, озвучивает через gTTS
5. Собирает видео MoviePy + FFmpeg
6. Отправляет в Telegram
7. Помечает тему как выполненную и коммитит изменения

## Секреты (обязательно добавить в Settings → Secrets and variables → Actions)

| Имя                  | Описание                          |
|----------------------|-----------------------------------|
| `GEMINI_API_KEY`     | Ключ Google AI Studio             |
| `PEXELS_API_KEY`     | Ключ Pexels API                   |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather          |
| `TELEGRAM_CHAT_ID`   | ID чата/канала для отправки       |

## Первый запуск

1. Добавьте 4 секрета выше.
2. Перейдите во вкладку **Actions**.
3. Выберите workflow **Daily Facade Panels Video**.
4. Нажмите **Run workflow** → **Run workflow**.

После успешного прогона видео появится в указанном Telegram-чате.

## Локальный запуск (опционально)

```bash
export GEMINI_API_KEY=...
export PEXELS_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
pip install -r requirements.txt
python main.py
python send_to_telegram.py
```

---
*Автоматически создано по ТЗ.*
