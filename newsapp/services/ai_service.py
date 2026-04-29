from openai import OpenAI
from flask import current_app
from textwrap import shorten
import os

from ..models import Article


def _get_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY") or current_app.config.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    
    return OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )


def summarize_article(article: Article) -> str:
    """Use Groq to summarize an article into a short Vietnamese summary."""
    client = _get_client()

    model_name = current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Limit content length to keep prompt reasonable
    raw_text = f"Tiêu đề: {article.title}\n\nNội dung:\n{article.content}"
    prompt_text = shorten(raw_text, width=12000, placeholder="...")

    resp = client.chat.completions.create(
        model=model_name,
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
        max_tokens=250,
    )

    summary = (resp.choices[0].message.content or "").strip()
    return summary