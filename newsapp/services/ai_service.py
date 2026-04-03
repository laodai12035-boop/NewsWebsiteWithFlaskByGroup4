from __future__ import annotations

import os
from textwrap import shorten

from flask import current_app
from openai import OpenAI

from ..models import Article


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY") or current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=api_key)


def summarize_article(article: Article) -> str:
    """Use OpenAI to summarize an article into a short Vietnamese summary."""
    client = _get_client()

    # Limit content length to keep prompt reasonable
    raw_text = f"Tiêu đề: {article.title}\n\nNội dung:\n{article.content}"
    prompt_text = shorten(raw_text, width=6000, placeholder="...")

    resp = client.chat.completions.create(
        model=current_app.config.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là biên tập viên tin tức tiếng Việt. "
                    "Hãy tóm tắt bài báo dưới 120 từ, giữ văn phong báo chí, "
                    "nêu rõ ý chính và bối cảnh quan trọng."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        temperature=0.3,
        max_tokens=220,
    )

    summary = (resp.choices[0].message.content or "").strip()
    return summary

