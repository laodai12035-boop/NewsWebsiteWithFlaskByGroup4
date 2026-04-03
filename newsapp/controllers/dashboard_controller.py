from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_

from ..extensions import db
from ..models import Article, ArticleStatus, Category, Tag, User, UserRole
from ..services import article_service
from ..utils.auth import get_current_user, login_required
from ..utils.uploads import save_image_upload

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
def dashboard_home():
    user = get_current_user()
    assert user is not None

    if user.role == UserRole.EDITOR:
        pending_count = Article.query.filter(Article.status == ArticleStatus.PENDING).count()
        return render_template("dashboard_home.html", user=user, pending_count=pending_count)
    if user.role == UserRole.ADMIN:
        pending_count = Article.query.filter(Article.status == ArticleStatus.PENDING).count()
        users_count = User.query.count()
        
        # Data cho Chart: Số lượng bài viết theo Category
        categories = Category.query.all()
        chart_labels = []
        chart_data = []
        for cat in categories:
            count = Article.query.filter_by(category_id=cat.id).count()
            chart_labels.append(cat.name)
            chart_data.append(count)
        users_count = User.query.count()
        return render_template(
            "dashboard_home.html",
            user=user,
            pending_count=pending_count,
            users_count=users_count,
            chart_labels=chart_labels,
            chart_data=chart_data
        )

    # Author/User view
    return redirect(url_for("dashboard.my_articles"))


@bp.route("/articles")
@login_required
def my_articles():
    user = get_current_user()
    assert user is not None

    q = (request.args.get("q") or "").strip()
    status = request.args.get("status") or ""
    sort = request.args.get("sort") or "newest"

    query = Article.query.filter(Article.user_id == user.id)

    if status in ArticleStatus.ALL:
        query = query.filter(Article.status == status)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.excerpt.ilike(like), Article.content.ilike(like)))

    if sort == "oldest":
        query = query.order_by(Article.created_at.asc())
    elif sort == "views":
        query = query.order_by(Article.views.desc(), Article.created_at.desc())
    else:
        query = query.order_by(Article.created_at.desc())

    articles = query.all()
    return render_template("dashboard_articles.html", user=user, articles=articles, q=q, status=status, sort=sort)


@bp.route("/articles/create", methods=["GET", "POST"])
@login_required
def create_article():
    user = get_current_user()
    assert user is not None

    if user.role not in (UserRole.ADMIN, UserRole.EDITOR, UserRole.AUTHOR):
        flash("Bạn không có quyền viết bài.", "error")
        return redirect(url_for("dashboard.dashboard_home"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        excerpt = (request.form.get("excerpt") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        category_id = request.form.get("category_id") or ""
        action = request.form.get("action") or "save"

        if not title or not content or not category_id.isdigit():
            flash("Vui lòng nhập đầy đủ: tiêu đề, nội dung, danh mục.", "error")
            return redirect(url_for("dashboard.create_article"))

        upload = save_image_upload(request.files.get("image_file"))
        if not upload.ok:
            flash(upload.error or "Upload ảnh thất bại.", "error")
            return redirect(url_for("dashboard.create_article"))

        status = ArticleStatus.DRAFT
        if action == "submit":
            status = ArticleStatus.PENDING if user.role == UserRole.AUTHOR else ArticleStatus.PUBLISHED

        article = Article(
            title=title,
            content=content,
            excerpt=excerpt[:500] if excerpt else None,
            image_ref=upload.static_path or (image_url or None),
            user_id=user.id,
            category_id=int(category_id),
            status=status,
            meta_title=(request.form.get("meta_title") or "").strip()[:255] or None,
            meta_description=(request.form.get("meta_description") or "").strip()[:500] or None,
        )
        
        # Xử lý tags
        tags_str = (request.form.get("tags") or "").strip()
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
            for name in tag_names:
                slug = name.lower().replace(" ", "-")
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name, slug=slug)
                article.tags.append(tag)

        db.session.add(article)
        db.session.commit()

        if status == ArticleStatus.PENDING:
            flash("Đã nộp bài chờ duyệt.", "success")
        elif status == ArticleStatus.PUBLISHED:
            flash("Bài viết đã được xuất bản.", "success")
        else:
            flash("Đã lưu nháp.", "success")

        return redirect(url_for("dashboard.my_articles"))

    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    return render_template("article_form.html", categories=categories, article=None, mode="create")


@bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
def edit_article(article_id: int):
    user = get_current_user()
    assert user is not None

    article = Article.query.get_or_404(article_id)

    can_edit = False
    if user.role in (UserRole.ADMIN, UserRole.EDITOR):
        can_edit = True
    elif user.role == UserRole.AUTHOR and article.user_id == user.id and article.status in (
        ArticleStatus.DRAFT,
        ArticleStatus.PENDING,
        ArticleStatus.REJECTED,
    ):
        can_edit = True

    if not can_edit:
        flash("Bạn không có quyền chỉnh sửa bài viết này.", "error")
        return redirect(url_for("dashboard.my_articles"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        excerpt = (request.form.get("excerpt") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        category_id = request.form.get("category_id") or ""
        action = request.form.get("action") or "save"

        if not title or not content or not category_id.isdigit():
            flash("Vui lòng nhập đầy đủ: tiêu đề, nội dung, danh mục.", "error")
            return redirect(url_for("dashboard.edit_article", article_id=article_id))

        upload = save_image_upload(request.files.get("image_file"))
        if not upload.ok:
            flash(upload.error or "Upload ảnh thất bại.", "error")
            return redirect(url_for("dashboard.edit_article", article_id=article_id))

        article.title = title
        article.content = content
        article.excerpt = excerpt[:500] if excerpt else None
        article.category_id = int(category_id)
        article.meta_title = (request.form.get("meta_title") or "").strip()[:255] or None
        article.meta_description = (request.form.get("meta_description") or "").strip()[:500] or None

        if upload.static_path:
            article.image_ref = upload.static_path
        elif image_url:
            article.image_ref = image_url

        # Cập nhật tags
        tags_str = (request.form.get("tags") or "").strip()
        article.tags.clear()
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
            for name in tag_names:
                slug = name.lower().replace(" ", "-")
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name, slug=slug)
                article.tags.append(tag)

        if user.role == UserRole.AUTHOR and action == "submit":
            article_service.submit_for_review(article)
            flash("Đã nộp bài chờ duyệt.", "success")
        else:
            db.session.commit()
            flash("Cập nhật bài viết thành công!", "success")

        return redirect(url_for("dashboard.my_articles"))

    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()
    return render_template("article_form.html", article=article, categories=categories, mode="edit")


@bp.route("/articles/<int:article_id>/submit", methods=["POST"])
@login_required
def submit_article(article_id: int):
    user = get_current_user()
    assert user is not None

    article = Article.query.get_or_404(article_id)
    if user.role != UserRole.AUTHOR or article.user_id != user.id:
        flash("Bạn không có quyền nộp bài này.", "error")
        return redirect(url_for("dashboard.my_articles"))

    if article.status not in (ArticleStatus.DRAFT, ArticleStatus.REJECTED):
        flash("Bài viết không ở trạng thái có thể nộp.", "error")
        return redirect(url_for("dashboard.my_articles"))

    article_service.submit_for_review(article)
    flash("Đã nộp bài chờ duyệt.", "success")
    return redirect(url_for("dashboard.my_articles"))


@bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@login_required
def delete_article(article_id: int):
    user = get_current_user()
    assert user is not None

    article = Article.query.get_or_404(article_id)

    can_delete = user.role == UserRole.ADMIN or (
        user.role == UserRole.AUTHOR and article.user_id == user.id and article.status != ArticleStatus.PUBLISHED
    )
    if not can_delete:
        flash("Bạn không có quyền xóa bài viết này.", "error")
        return redirect(url_for("dashboard.my_articles"))

    db.session.delete(article)
    db.session.commit()
    flash("Xóa bài viết thành công!", "success")
    return redirect(url_for("dashboard.my_articles"))


@bp.route("/uploads/images", methods=["POST"])
@login_required
def upload_inline_image():
    """Upload ảnh dùng trong nội dung bài viết, trả về URL để chèn vào textarea."""
    user = get_current_user()
    assert user is not None

    if user.role not in (UserRole.ADMIN, UserRole.EDITOR, UserRole.AUTHOR, UserRole.USER):
        return jsonify({"ok": False, "error": "Bạn không có quyền upload hình ảnh."}), 403

    upload = save_image_upload(request.files.get("file"))
    if not upload.ok:
        return jsonify({"ok": False, "error": upload.error or "Upload ảnh thất bại."}), 400

    url = url_for("static", filename=upload.static_path, _external=False)
    return jsonify({"ok": True, "url": url})

