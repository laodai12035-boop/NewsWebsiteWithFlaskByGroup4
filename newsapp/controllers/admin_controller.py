from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from ..extensions import db
from ..models import Category, User, UserRole
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
    return render_template("admin_users.html", users=users, q=q, role=role, active=active)


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

    return render_template("admin_user_form.html", user=None, roles=sorted(UserRole.ALL))


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

    return render_template("admin_user_form.html", user=user, roles=sorted(UserRole.ALL))


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
    return render_template("admin_categories.html", categories=categories, q=q, active=active)


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

    return render_template("admin_category_form.html", category=None)


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
    return render_template("admin_category_form.html", category=category)


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

