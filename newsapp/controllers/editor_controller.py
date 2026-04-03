from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from ..extensions import db
from ..models import Article, ArticleStatus, Category, Comment, CommentStatus, UserRole
from ..services import article_service
from ..utils.auth import get_current_user, roles_required

bp = Blueprint("editor", __name__, url_prefix="/editor")


@bp.route("/review")
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def review_queue():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category")
    sort = request.args.get("sort") or "newest"

    query = Article.query.filter(Article.status == ArticleStatus.PENDING)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like)))

    if category_id and category_id.isdigit():
        query = query.filter(Article.category_id == int(category_id))

    if sort == "oldest":
        query = query.order_by(Article.created_at.asc())
    else:
        query = query.order_by(Article.created_at.desc())

    articles = query.all()
    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    return render_template(
        "editor_review.html",
        articles=articles,
        categories=categories,
        q=q,
        selected_category=category_id or "",
        sort=sort,
    )


@bp.route("/articles/<int:article_id>/approve", methods=["POST"])
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def approve_article(article_id: int):
    article = Article.query.get_or_404(article_id)
    if article.status != ArticleStatus.PENDING:
        flash("Bài viết không ở trạng thái chờ duyệt.", "error")
        return redirect(url_for("editor.review_queue"))

    article_service.approve(article)
    flash("Đã duyệt và xuất bản bài viết.", "success")
    return redirect(url_for("editor.review_queue"))


@bp.route("/articles/<int:article_id>/reject", methods=["POST"])
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def reject_article(article_id: int):
    article = Article.query.get_or_404(article_id)
    if article.status != ArticleStatus.PENDING:
        flash("Bài viết không ở trạng thái chờ duyệt.", "error")
        return redirect(url_for("editor.review_queue"))

    note = (request.form.get("note") or "").strip()
    article_service.reject(article, note=note)
    flash("Đã từ chối bài viết.", "success")
    return redirect(url_for("editor.review_queue"))


@bp.route("/articles/<int:article_id>/unpublish", methods=["POST"])
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def unpublish_article(article_id: int):
    article = Article.query.get_or_404(article_id)
    if article.status != ArticleStatus.PUBLISHED:
        flash("Chỉ có thể gỡ bài đã xuất bản.", "error")
        return redirect(url_for("main.article_detail", article_id=article_id))

    article_service.unpublish(article)
    flash("Đã gỡ bài khỏi trang chủ.", "success")
    return redirect(url_for("main.article_detail", article_id=article_id))


# --- Duyệt bình luận ---


@bp.route("/comments")
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def review_comments():
    status_filter = request.args.get("status") or "pending"
    q = (request.args.get("q") or "").strip()

    query = Comment.query
    if status_filter in CommentStatus.ALL:
        query = query.filter(Comment.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(Comment.content.ilike(like))

    comments = query.order_by(Comment.created_at.desc()).all()
    return render_template(
        "editor_comments.html",
        comments=comments,
        status_filter=status_filter,
        q=q,
    )


@bp.route("/comments/<int:comment_id>/approve", methods=["POST"])
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def approve_comment(comment_id: int):
    comment = Comment.query.get_or_404(comment_id)
    if comment.status != CommentStatus.PENDING:
        flash("Bình luận không ở trạng thái chờ duyệt.", "error")
        return redirect(url_for("editor.review_comments"))

    comment.status = CommentStatus.APPROVED
    comment.review_note = None
    db.session.commit()
    flash("Đã duyệt bình luận.", "success")
    return redirect(url_for("editor.review_comments"))


@bp.route("/comments/<int:comment_id>/reject", methods=["POST"])
@roles_required(UserRole.EDITOR, UserRole.ADMIN)
def reject_comment(comment_id: int):
    comment = Comment.query.get_or_404(comment_id)
    if comment.status != CommentStatus.PENDING:
        flash("Bình luận không ở trạng thái chờ duyệt.", "error")
        return redirect(url_for("editor.review_comments"))

    note = (request.form.get("note") or "").strip()[:500]
    comment.status = CommentStatus.REJECTED
    comment.review_note = note or "Từ chối bình luận."
    db.session.commit()
    flash("Đã từ chối bình luận.", "success")
    return redirect(url_for("editor.review_comments"))

