from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from ..extensions import db
from ..models import Article, ArticleStatus, Category, User, UserRole
from ..services import admin_service, auth_service
from ..utils.auth import roles_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users")
@roles_required(UserRole.ADMIN)
def users_list():
    q = (request.args.get("q") or "").strip()
    role = request.args.get("role") or ""
    active = request.args.get("active") or ""

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))
    if role in UserRole.ALL:
        query = query.filter(User.role == role)
    if active in ("true", "false"):
        query = query.filter(User.active == (active == "true"))

    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users, q=q, role=role, active=active)


@bp.route("/users/create", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN)
def user_create():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or UserRole.USER
        active = (request.form.get("active") == "on")

        if not username or not email or not password:
            flash("Vui lòng nhập đầy đủ username/email/password.", "error")
            return redirect(url_for("admin.user_create"))
        if role not in UserRole.ALL:
            flash("Role không hợp lệ.", "error")
            return redirect(url_for("admin.user_create"))
        if User.query.filter_by(username=username).first():
            flash("Username đã tồn tại.", "error")
            return redirect(url_for("admin.user_create"))
        if User.query.filter_by(email=email.lower()).first():
            flash("Email đã tồn tại.", "error")
            return redirect(url_for("admin.user_create"))

        auth_service.create_user(username=username, email=email, password=password, role=role, active=active)
        flash("Tạo user thành công.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/user_form.html", user=None, roles=sorted(UserRole.ALL))


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN)
def user_edit(user_id: int):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.email = (request.form.get("email") or "").strip().lower()
        role = request.form.get("role") or user.role
        user.active = (request.form.get("active") == "on")
        new_password = (request.form.get("new_password") or "").strip()

        if role not in UserRole.ALL:
            flash("Role không hợp lệ.", "error")
            return redirect(url_for("admin.user_edit", user_id=user_id))

        user.role = role
        db.session.commit()

        if new_password:
            auth_service.set_password(user, new_password)

        flash("Cập nhật user thành công.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/user_form.html", user=user, roles=sorted(UserRole.ALL))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@roles_required(UserRole.ADMIN)
def user_delete(user_id: int):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("Đã xóa user.", "success")
    return redirect(url_for("admin.users_list"))


@bp.route("/categories")
@roles_required(UserRole.ADMIN)
def categories_list():
    q = (request.args.get("q") or "").strip()
    active = request.args.get("active") or ""

    query = Category.query
    if q:
        like = f"%{q}%"
        query = query.filter(Category.name.ilike(like))
    if active in ("true", "false"):
        query = query.filter(Category.active == (active == "true"))

    categories = query.order_by(Category.name.asc()).all()
    return render_template("admin/categories.html", categories=categories, q=q, active=active)


@bp.route("/categories/create", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN)
def category_create():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        active = (request.form.get("active") == "on")

        if not name:
            flash("Vui lòng nhập tên danh mục.", "error")
            return redirect(url_for("admin.category_create"))
        if Category.query.filter_by(name=name).first():
            flash("Danh mục đã tồn tại.", "error")
            return redirect(url_for("admin.category_create"))

        cat = Category(name=name, description=description or None, active=active)
        db.session.add(cat)
        db.session.commit()
        flash("Tạo danh mục thành công.", "success")
        return redirect(url_for("admin.categories_list"))

    return render_template("admin/category_form.html", category=None)


@bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN)
def category_edit(category_id: int):
    category = Category.query.get_or_404(category_id)
    if request.method == "POST":
        category.name = (request.form.get("name") or "").strip()
        category.description = (request.form.get("description") or "").strip() or None
        category.active = (request.form.get("active") == "on")
        db.session.commit()
        flash("Cập nhật danh mục thành công.", "success")
        return redirect(url_for("admin.categories_list"))
    return render_template("admin/category_form.html", category=category)


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@roles_required(UserRole.ADMIN)
def category_delete(category_id: int):
    category = Category.query.get_or_404(category_id)
    if category.articles and len(category.articles) > 0:
        flash("Không thể xóa danh mục đang có bài viết.", "error")
        return redirect(url_for("admin.categories_list"))
    db.session.delete(category)
    db.session.commit()
    flash("Đã xóa danh mục.", "success")
    return redirect(url_for("admin.categories_list"))


@bp.route("/backup", methods=["POST"])
@roles_required(UserRole.ADMIN)
def backup():
    try:
        path = admin_service.backup_database()
    except Exception as e:
        flash(f"Backup thất bại: {e}", "error")
        return redirect(url_for("dashboard.dashboard_home"))

    flash("Đã tạo backup database.", "success")
    return send_file(path, as_attachment=True)


@bp.route("/analytics")
@roles_required(UserRole.ADMIN)
def analytics():
    # Get basic statistics
    stats = get_dashboard_stats()
    
    return render_template("admin/analytics.html", stats=stats)


@bp.route("/api/stats")
@roles_required(UserRole.ADMIN)
def api_stats():
    """API endpoint for real-time statistics"""
    time_range = request.args.get('range', '30', type=int)
    stats = get_dashboard_stats(time_range)
    return jsonify(stats)


@bp.route("/api/articles-over-time")
@roles_required(UserRole.ADMIN)
def api_articles_over_time():
    """API endpoint for articles timeline data"""
    days = request.args.get('days', 30, type=int)
    
    # Get articles created in the last N days
    start_date = datetime.now() - timedelta(days=days)
    
    # Query articles grouped by date and status
    articles_data = db.session.query(
        func.date(Article.created_at).label('date'),
        Article.status,
        func.count(Article.id).label('count')
    ).filter(
        Article.created_at >= start_date
    ).group_by(
        func.date(Article.created_at),
        Article.status
    ).order_by('date').all()
    
    # Format data for Chart.js
    dates = []
    published_data = []
    draft_data = []
    pending_data = []
    
    # Create date range
    current_date = start_date.date()
    end_date = datetime.now().date()
    
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        
        # Find counts for this date
        published_count = 0
        draft_count = 0
        pending_count = 0
        
        for item in articles_data:
            if item.date == current_date:
                if item.status == ArticleStatus.PUBLISHED:
                    published_count = item.count
                elif item.status == ArticleStatus.DRAFT:
                    draft_count = item.count
                elif item.status == ArticleStatus.PENDING:
                    pending_count = item.count
        
        published_data.append(published_count)
        draft_data.append(draft_count)
        pending_data.append(pending_count)
        
        current_date += timedelta(days=1)
    
    return jsonify({
        'labels': dates,
        'datasets': [
            {
                'label': 'Published',
                'data': published_data,
                'borderColor': '#3b82f6',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)'
            },
            {
                'label': 'Draft',
                'data': draft_data,
                'borderColor': '#f59e0b',
                'backgroundColor': 'rgba(245, 158, 11, 0.1)'
            },
            {
                'label': 'Pending',
                'data': pending_data,
                'borderColor': '#ef4444',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)'
            }
        ]
    })


@bp.route("/api/category-views")
@roles_required(UserRole.ADMIN)
def api_category_views():
    """API endpoint for views by category"""
    
    # Query total views by category
    category_data = db.session.query(
        Category.name,
        func.sum(Article.views).label('total_views')
    ).join(
        Article, Category.id == Article.category_id
    ).filter(
        Article.status == ArticleStatus.PUBLISHED
    ).group_by(
        Category.name
    ).order_by(
        func.sum(Article.views).desc()
    ).limit(10).all()
    
    labels = [item.name for item in category_data]
    data = [int(item.total_views or 0) for item in category_data]
    
    return jsonify({
        'labels': labels,
        'data': data
    })


@bp.route("/api/user-growth")
@roles_required(UserRole.ADMIN)
def api_user_growth():
    """API endpoint for user growth over time"""
    months = request.args.get('months', 6, type=int)
    
    # Get user registrations by month
    start_date = datetime.now() - timedelta(days=months * 30)
    
    user_data = db.session.query(
        func.date_trunc('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date_trunc('month', User.created_at)
    ).order_by('month').all()
    
    labels = []
    data = []
    
    for item in user_data:
        labels.append(item.month.strftime('%B %Y'))
        data.append(item.count)
    
    return jsonify({
        'labels': labels,
        'data': data
    })


@bp.route("/api/top-articles")
@roles_required(UserRole.ADMIN)
def api_top_articles():
    """API endpoint for top performing articles"""
    limit = request.args.get('limit', 10, type=int)
    
    top_articles = db.session.query(
        Article.title,
        Article.views
    ).filter(
        Article.status == ArticleStatus.PUBLISHED
    ).order_by(
        Article.views.desc()
    ).limit(limit).all()
    
    labels = [article.title[:50] + '...' if len(article.title) > 50 else article.title for article in top_articles]
    data = [article.views for article in top_articles]
    
    return jsonify({
        'labels': labels,
        'data': data
    })


def get_dashboard_stats(days=30):
    """Get dashboard statistics"""
    start_date = datetime.now() - timedelta(days=days)
    
    # Total articles
    total_articles = Article.query.count()
    
    # Published articles
    published_articles = Article.query.filter_by(status=ArticleStatus.PUBLISHED).count()
    
    # Active users (users who logged in or created content in the last N days)
    active_users = User.query.filter(
        User.created_at >= start_date
    ).count()
    
    # Today's views
    today = datetime.now().date()
    today_views = db.session.query(
        func.sum(Article.views)
    ).filter(
        Article.status == ArticleStatus.PUBLISHED
    ).scalar() or 0
    
    return {
        'total_articles': total_articles,
        'published_articles': published_articles,
        'active_users': active_users,
        'today_views': int(today_views)
    }

