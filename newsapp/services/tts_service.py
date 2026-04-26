from __future__ import annotations

import asyncio
import logging
import os
from typing import Tuple

import edge_tts
from flask import current_app

from ..models import Article

logger = logging.getLogger(__name__)

# Giọng đọc tiếng Việt (Microsoft Neural Voices – miễn phí)
# vi-VN-HoaiMyNeural  = Nữ
# vi-VN-NamMinhNeural = Nam
DEFAULT_VOICE = "vi-VN-HoaiMyNeural"


def _build_text(article: Article) -> str:
    """Compose text to read aloud."""
    parts = [article.title or ""]
    if article.excerpt:
        parts.append(article.excerpt)
    parts.append(article.content or "")
    return ". ".join(p.strip() for p in parts if p and p.strip())


async def _edge_tts_save(text: str, voice: str, path: str) -> None:
    """Generate audio with edge-tts and write to *path*."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def generate_tts(article: Article) -> Tuple[str, int]:
    """Generate or reuse TTS audio for an article.

    Returns (static_path, duration_seconds_guess).
    """
    text = _build_text(article)
    if not text:
        raise ValueError("Article has no content to read.")

    out_dir = os.path.join(current_app.static_folder, "audio", "articles")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"article_{article.id}.mp3"
    abs_path = os.path.join(out_dir, filename)

    voice = current_app.config.get("TTS_VOICE", DEFAULT_VOICE)

    # Chỉ generate mới nếu file chưa tồn tại hoặc quá nhỏ (< 1 KB).
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) < 1000:
        generated = False
        last_error = None
        for attempt in range(2):
            try:
                logger.info("TTS attempt %d for article %s", attempt + 1, article.id)
                asyncio.run(_edge_tts_save(text, voice, abs_path))

                if os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
                    generated = True
                    logger.info("TTS generated successfully: %s (%d bytes)",
                                filename, os.path.getsize(abs_path))
                    break
            except Exception as exc:
                last_error = exc
                logger.warning("TTS attempt %d failed: %s", attempt + 1, exc)
                continue
        if not generated:
            raise Exception(f"TTS generation failed after 2 attempts: {last_error}")

    # Ước lượng thời gian đọc
    word_count = max(1, len(text.split()))
    duration_sec = int(word_count / 2.5)

    static_path = f"audio/articles/{filename}"
    return static_path, duration_sec