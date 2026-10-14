#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Контент-завод: генерация видео о фасадных панелях.
"""
import json
import os
import sys
import traceback
from pathlib import Path

import requests
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

from config import (
    PEXELS_API_KEY,
    FONT_PATH,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    FPS,
)

CONTENT_PLAN = Path("content_plan.json")
OUTPUT_VIDEO = Path("output.mp4")
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)


def log(msg: str):
    print(f"[LOG] {msg}", flush=True)


def load_plan():
    with open(CONTENT_PLAN, "r", encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan):
    with open(CONTENT_PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def get_next_lesson(plan):
    for item in plan:
        if not item.get("done", False):
            return item
    return None


def generate_script(topic: str) -> list:
    """Agnes 2.5 Flash → список слайдов [{text, keywords}]"""
    key = os.getenv("AGNES_API_KEY")
    if not key:
        raise RuntimeError("AGNES_API_KEY не задан")

    url = "https://apihub.agnes-ai.com/v1/chat/completions"
    prompt = f"""
Ты — эксперт по строительству и фасадным материалам.
Тема видео: «{topic}».

Сгенерируй сценарий из 6–8 коротких слайдов для образовательного видео.
Каждый слайд — один кадр с текстом на экране и озвучкой.

Верни ТОЛЬКО валидный JSON-массив объектов вида:
[
  {{"text": "Краткий текст слайда (1-2 предложения, до 120 символов)", "keywords": "english keywords for stock photo, 2-4 words"}},
  ...
]

Требования:
- Текст на русском, простой и понятный.
- keywords — на английском, подходящие для поиска фото на Pexels (фасады домов, панели, строительство).
- Не более 8 слайдов.
- Никакого дополнительного текста вне JSON.
"""

    payload = {
        "model": "agnes-2.5-flash",
        "messages": [
            {"role": "system", "content": "Ты генерируешь только валидный JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.55,
        "max_tokens": 2000,
        "stream": False,
    }

    log(f"Запрос сценария к Agnes по теме: {topic}")
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        slides = json.loads(text)
        if not isinstance(slides, list) or len(slides) < 6:
            raise ValueError("Слишком мало слайдов")
        return slides[:8]
    except Exception as e:
        log(f"Ошибка парсинга ответа Agnes: {e}\nОтвет: {text[:500]}")
        raise


def download_pexels_photo(keywords: str) -> Path:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY не задан")

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": keywords,
        "per_page": 5,
        "orientation": "landscape",
        "size": "large",
    }
    log(f"Поиск фото на Pexels: {keywords}")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    photos = data.get("photos", [])
    if not photos:
        raise RuntimeError(f"Фото по запросу '{keywords}' не найдены")

    photo = photos[0]
    src = photo["src"].get("large") or photo["src"].get("medium") or photo["src"]["original"]
    img_path = TEMP_DIR / f"bg_{hash(keywords) % 100000}.jpg"
    r = requests.get(src, timeout=30)
    r.raise_for_status()
    img_path.write_bytes(r.content)
    log(f"Скачано фото: {img_path.name}")
    return img_path


def create_slide_image(bg_path: Path, text: str, out_path: Path):
    """Накладывает текст на фото с полупрозрачной подложкой."""
    img = Image.open(bg_path).convert("RGB")
    img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img, "RGBA")

    font = None
    font_candidates = [
        FONT_PATH,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for fp in font_candidates:
        try:
            font = ImageFont.truetype(fp, 60)
            log(f"Шрифт загружен: {fp}")
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
        log("Шрифт не найден, используем стандартный (может не поддерживать кириллицу)")

    margin = 40
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    box_w = min(text_w + margin * 2, VIDEO_WIDTH - 80)
    box_h = text_h + margin * 2
    box_x = (VIDEO_WIDTH - box_w) // 2
    box_y = VIDEO_HEIGHT - box_h - 60

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=20,
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    text_x = box_x + (box_w - text_w) // 2
    text_y = box_y + (box_h - text_h) // 2
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

    img.save(out_path, "JPEG", quality=90)
    return out_path


def generate_tts(text: str, out_path: Path):
    log("Генерация озвучки...")
    tts = gTTS(text=text, lang="ru", slow=False)
    tts.save(str(out_path))
    return out_path


def build_video(slides_data: list) -> Path:
    clips = []
    for i, slide in enumerate(slides_data):
        text = slide["text"]
        keywords = slide.get("keywords", "house facade panels")
        log(f"Слайд {i+1}/{len(slides_data)}: {text[:50]}...")

        bg = download_pexels_photo(keywords)
        img_path = TEMP_DIR / f"slide_{i:02d}.jpg"
        create_slide_image(bg, text, img_path)

        audio_path = TEMP_DIR / f"audio_{i:02d}.mp3"
        generate_tts(text, audio_path)

        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration
        image_clip = ImageClip(str(img_path), duration=duration)
        video_clip = image_clip.set_audio(audio_clip)
        clips.append(video_clip)

    log("Склейка клипов...")
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        str(OUTPUT_VIDEO),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(TEMP_DIR / "temp-audio.m4a"),
        remove_temp=True,
        logger=None,
    )
    final.close()
    for c in clips:
        c.close()
    return OUTPUT_VIDEO


def compress_video(src: Path) -> Path:
    """Сжатие через FFmpeg до ~45 МБ."""
    compressed = Path("output_compressed.mp4")
    cmd = (
        f'ffmpeg -y -i "{src}" -vf scale=1280:720 -c:v libx264 -b:v 1200k '
        f'-c:a aac -b:a 128k -movflags +faststart "{compressed}"'
    )
    log("Сжатие видео...")
    ret = os.system(cmd)
    if ret != 0:
        log("Предупреждение: сжатие не удалось, используем оригинал")
        return src
    src.unlink(missing_ok=True)
    compressed.rename(src)
    return src


def main():
    try:
        plan = load_plan()
        lesson = get_next_lesson(plan)
        if not lesson:
            log("Все уроки уже обработаны. Завершение.")
            return

        topic = lesson["topic"]
        log(f"=== Обработка урока #{lesson['id']}: {topic} ===")

        slides = generate_script(topic)
        log(f"Получено слайдов: {len(slides)}")

        video_path = build_video(slides)
        video_path = compress_video(video_path)

        size_mb = video_path.stat().st_size / (1024 * 1024)
        log(f"Видео готово: {video_path} ({size_mb:.1f} МБ)")

        lesson["done"] = True
        save_plan(plan)
        log("content_plan.json обновлён")

        with open("current_topic.txt", "w", encoding="utf-8") as f:
            f.write(topic)

    except Exception as e:
        log(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
