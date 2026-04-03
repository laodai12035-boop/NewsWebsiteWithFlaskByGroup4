from __future__ import annotations
from flask import send_file
import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from ..extensions import db
from ..models import Article, ArticleStatus, Category, Comment, CommentStatus, Favorite
from ..services import tts_service
from ..utils.auth import get_current_user, login_required

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category")
    sort = request.args.get("sort") or "newest"

    query = Article.query.filter(Article.status == ArticleStatus.PUBLISHED)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like)))

    if category_id and category_id.isdigit():
        query = query.filter(Article.category_id == int(category_id))

    if sort == "views":
        query = query.order_by(Article.views.desc(), Article.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Article.created_at.asc())
    else:
        query = query.order_by(Article.created_at.desc())

    articles = query.limit(20).all()
    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    return render_template(
        "index.html",
        articles=articles,
        categories=categories,
        q=q,
        selected_category=category_id or "",
        sort=sort,
    )


@bp.route("/article/<int:article_id>")
def article_detail(article_id: int):
    article = Article.query.get_or_404(article_id)
    if article.status != ArticleStatus.PUBLISHED:
        user = get_current_user()
        if not user:
            flash("Bài viết này chưa được xuất bản.", "error")
            return redirect(url_for("main.index"))
        if user.role not in ("admin", "editor") and article.user_id != user.id:
            flash("Bạn không có quyền xem bài viết này.", "error")
            return redirect(url_for("main.index"))
    if article.status == ArticleStatus.PUBLISHED:
        article.views += 1
        db.session.commit()
    user = get_current_user()
    is_favorited = False
    if user:
        is_favorited = (
            Favorite.query.filter_by(article_id=article.id, user_id=user.id).first()
            is not None
        )
    # Chỉ hiển thị bình luận đã được duyệt (approved)
    approved_comments = (
        Comment.query.filter_by(article_id=article.id, status=CommentStatus.APPROVED)
        .order_by(Comment.created_at.desc())
        .all()
    )
    enable_ai_summary = bool(current_app.config.get("OPENAI_API_KEY"))
    return render_template(
        "article_detail.html",
        article=article,
        is_favorited=is_favorited,
        approved_comments=approved_comments,
        enable_ai_summary=enable_ai_summary,
    )


@bp.route("/article/<int:article_id>/tts", methods=["GET"])
def article_tts(article_id: int):
    """Generate or return existing TTS audio for an article."""
    article = Article.query.get_or_404(article_id)

    # Kiểm tra quyền
    if article.status != ArticleStatus.PUBLISHED:
        user = get_current_user()
        if not user or (user.role not in ("admin", "editor") and article.user_id != user.id):
            flash("Bài viết này chưa được xuất bản.", "error")
            return redirect(url_for("main.index"))

    # Generate nếu chưa có
    if not article.audio_ref:
        try:
            static_path, duration = tts_service.generate_tts(article)
        except Exception as exc:
            flash(f"Không thể tạo audio: {exc}", "error")
            return redirect(url_for("main.article_detail", article_id=article.id))

        article.audio_ref = static_path
        article.audio_duration = duration
        db.session.commit()

    # 👉 Lấy đường dẫn file thật
    base_dir = current_app.config["BASE_DIR"]
    abs_path = os.path.join(base_dir, "static", article.audio_ref)

    # 👉 TRẢ AUDIO INLINE (KHÔNG DOWNLOAD)
    return send_file(
        abs_path,
        mimetype="audio/mpeg",
        as_attachment=False
    )

@bp.route("/category/<int:category_id>")
def category_articles(category_id: int):
    category = Category.query.get_or_404(category_id)
    q = (request.args.get("q") or "").strip()
    sort = request.args.get("sort") or "newest"

    query = Article.query.filter(
        Article.category_id == category_id, Article.status == ArticleStatus.PUBLISHED
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like)))

    if sort == "views":
        query = query.order_by(Article.views.desc(), Article.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Article.created_at.asc())
    else:
        query = query.order_by(Article.created_at.desc())

    articles = query.all()
    return render_template("category.html", category=category, articles=articles, q=q, sort=sort)


@bp.route("/article/<int:article_id>/comment", methods=["POST"])
@login_required
def add_comment(article_id: int):
    user = get_current_user()
    assert user is not None

    article = Article.query.get_or_404(article_id)
    # Tôn trọng quyền xem giống article_detail
    if article.status != ArticleStatus.PUBLISHED and user.role not in ("admin", "editor") and article.user_id != user.id:
        flash("Bạn không có quyền bình luận bài viết này.", "error")
        return redirect(url_for("main.index"))

    content = (request.form.get("content") or "").strip()
    if not content:
        flash("Nội dung bình luận không được để trống.", "error")
        return redirect(url_for("main.article_detail", article_id=article.id))

    if len(content) > 2000:
        content = content[:2000]

    comment = Comment(
        content=content,
        article_id=article.id,
        user_id=user.id,
        status=CommentStatus.PENDING,
    )
    db.session.add(comment)
    db.session.commit()
    flash("Bình luận đã gửi, đang chờ Admin/Editor duyệt.", "success")
    return redirect(url_for("main.article_detail", article_id=article.id))


@bp.route("/article/<int:article_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(article_id: int):
    user = get_current_user()
    assert user is not None

    article = Article.query.get_or_404(article_id)
    if article.status != ArticleStatus.PUBLISHED:
        flash("Chỉ có thể lưu bài đã xuất bản.", "error")
        return redirect(url_for("main.article_detail", article_id=article.id))

    fav = Favorite.query.filter_by(article_id=article.id, user_id=user.id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Đã bỏ khỏi mục yêu thích.", "info")
    else:
        fav = Favorite(article_id=article.id, user_id=user.id)
        db.session.add(fav)
        db.session.commit()
        flash("Đã lưu vào mục yêu thích.", "success")

    return redirect(url_for("main.article_detail", article_id=article.id))


@bp.route("/me/favorites")
@login_required
def my_favorites():
    user = get_current_user()
    assert user is not None

    q = (request.args.get("q") or "").strip()
    sort = request.args.get("sort") or "newest"

    # Lấy danh sách article mà user đã yêu thích
    fav_query = (
        Article.query.join(Favorite, Favorite.article_id == Article.id)
        .filter(Favorite.user_id == user.id, Article.status == ArticleStatus.PUBLISHED)
    )

    if q:
        like = f"%{q}%"
        fav_query = fav_query.filter(
            or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like))
        )

    if sort == "views":
        fav_query = fav_query.order_by(Article.views.desc(), Article.created_at.desc())
    elif sort == "oldest":
        fav_query = fav_query.order_by(Article.created_at.asc())
    else:
        fav_query = fav_query.order_by(Article.created_at.desc())

    articles = fav_query.all()
    return render_template("favorites.html", articles=articles, q=q, sort=sort)

