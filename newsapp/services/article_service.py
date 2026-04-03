from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models import Article, ArticleStatus


def submit_for_review(article: Article) -> None:
    if article.status in (ArticleStatus.DRAFT, ArticleStatus.REJECTED):
        article.status = ArticleStatus.PENDING
        article.review_note = None
        db.session.commit()


def approve(article: Article) -> None:
    article.status = ArticleStatus.PUBLISHED
    article.review_note = None
    article.published_at = datetime.utcnow()
    db.session.commit()


def reject(article: Article, note: str) -> None:
    article.status = ArticleStatus.REJECTED
    article.review_note = (note or "").strip()[:500] or "Từ chối: nội dung chưa phù hợp."
    db.session.commit()


def unpublish(article: Article) -> None:
    article.status = ArticleStatus.ARCHIVED
    db.session.commit()

