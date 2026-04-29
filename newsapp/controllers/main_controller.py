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

    # If category is selected, redirect to category page
    if category_id and category_id.isdigit():
        return redirect(url_for('main.category_articles', category_id=int(category_id), q=q, sort=sort))

    # Base query for published articles
    base_query = Article.query.filter(Article.status == ArticleStatus.PUBLISHED)
    
    # Featured articles (top 5 latest with high views)
    featured_articles = base_query.order_by(Article.views.desc(), Article.created_at.desc()).limit(5).all()
    
    # Most viewed articles (top 10)
    most_viewed_articles = base_query.order_by(Article.views.desc(), Article.created_at.desc()).limit(10).all()
    
    # Latest articles (top 12)
    latest_articles = base_query.order_by(Article.created_at.desc()).limit(12).all()
    
    # Get articles by category (top 3 for each category)
    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    category_articles = {}
    for category in categories:
        category_articles[category.id] = (
            base_query.filter(Article.category_id == category.id)
            .order_by(Article.created_at.desc())
            .limit(3)
            .all()
        )

    # Handle search and filtering
    query = base_query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like)))

    if sort == "views":
        query = query.order_by(Article.views.desc(), Article.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Article.created_at.asc())
    else:
        query = query.order_by(Article.created_at.desc())

    articles = query.limit(20).all()
    
    return render_template(
        "main/index.html",
        articles=articles,
        categories=categories,
        category_articles=category_articles,
        featured_articles=featured_articles,
        most_viewed_articles=most_viewed_articles,
        latest_articles=latest_articles,
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
    
    # Get related articles (same category, excluding current article)
    related_articles = (
        Article.query.filter(
            Article.category_id == article.category_id,
            Article.status == ArticleStatus.PUBLISHED,
            Article.id != article.id
        )
        .order_by(Article.created_at.desc())
        .limit(5)
        .all()
    )
    
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
    enable_ai_summary = bool(current_app.config.get("GROQ_API_KEY"))
    return render_template(
        "main/article_detail.html",
        article=article,
        user=user,
        is_favorited=is_favorited,
        approved_comments=approved_comments,
        related_articles=related_articles,
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

    # Kiểm tra file audio thực tế có tồn tại không
    need_generate = not article.audio_ref
    if article.audio_ref:
        abs_path = os.path.join(current_app.static_folder, article.audio_ref)
        if not os.path.exists(abs_path) or os.path.getsize(abs_path) < 1000:
            need_generate = True  # File bị xóa hoặc hỏng → tạo lại

    if need_generate:
        try:
            static_path, duration = tts_service.generate_tts(article)
        except Exception as exc:
            current_app.logger.error("TTS generation failed for article %s: %s", article.id, exc)
            flash(f"Không thể tạo audio: {exc}", "error")
            return redirect(url_for("main.article_detail", article_id=article.id))

        article.audio_ref = static_path
        article.audio_duration = duration
        db.session.commit()

    # Lấy đường dẫn file thật
    abs_path = os.path.join(current_app.static_folder, article.audio_ref)

    if not os.path.exists(abs_path):
        current_app.logger.error("TTS file not found: %s", abs_path)
        flash("File audio không tồn tại, vui lòng thử lại.", "error")
        return redirect(url_for("main.article_detail", article_id=article.id))

    # Trả audio inline (không download)
    return send_file(
        abs_path,
        mimetype="audio/mpeg",
        as_attachment=False
    )

@bp.route("/categories")
def categories():
    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    return render_template("main/categories.html", categories=categories)


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
    return render_template("main/category.html", category=category, articles=articles, q=q, sort=sort)


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
    return render_template("main/favorites.html", articles=articles, q=q, sort=sort)


@bp.route("/me/profile")
@login_required
def profile_dashboard():
    user = get_current_user()
    assert user is not None

    # Get user's articles with statistics
    user_articles = Article.query.filter_by(user_id=user.id).order_by(Article.created_at.desc()).all()
    
    # Calculate statistics
    published_count = len([a for a in user_articles if a.status == ArticleStatus.PUBLISHED])
    total_views = sum(a.views for a in user_articles if a.status == ArticleStatus.PUBLISHED)
    
    return render_template(
        "main/profile.html",
        user=user,
        user_articles=user_articles,
        published_count=published_count,
        total_views=total_views
    )

