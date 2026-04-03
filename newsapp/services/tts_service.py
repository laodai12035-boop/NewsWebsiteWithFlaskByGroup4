from __future__ import annotations

import os
from typing import Tuple

from flask import current_app
from gtts import gTTS

from ..models import Article


def _build_text(article: Article) -> str:
    """Compose text to read aloud."""
    parts = [article.title or ""]
    if article.excerpt:
        parts.append(article.excerpt)
    parts.append(article.content or "")
    return ". ".join(p.strip() for p in parts if p and p.strip())


def generate_tts(article: Article) -> Tuple[str, int]:
    """Generate or reuse TTS audio for an article.

    Returns (static_path, duration_seconds_guess).
    """
    text = _build_text(article)
    if not text:
        raise ValueError("Article has no content to read.")

    base_dir = current_app.config["BASE_DIR"]
    out_dir = os.path.join(base_dir, "static", "audio", "articles")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"article_{article.id}.mp3"
    abs_path = os.path.join(out_dir, filename)

    # ✅ Nếu đã có file → không generate lại
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) < 1000:
        for _ in range(2):
            try:
                tts = gTTS(text=text, lang="vi")
                tts.save(abs_path)

                if os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
                    break
            except Exception:
                continue
    else:
        raise Exception("TTS generation failed")

    # Ước lượng thời gian đọc
    word_count = max(1, len(text.split()))
    duration_sec = int(word_count / 2.5)

    static_path = f"audio/articles/{filename}"
    return static_path, duration_sec