from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..models import User
from ..services import auth_service
from ..extensions import db

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not username or not email or not password:
            flash("Vui lòng nhập đầy đủ thông tin.", "error")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Mật khẩu không khớp!", "error")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Tên người dùng đã tồn tại!", "error")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email.lower()).first():
            flash("Email đã được sử dụng!", "error")
            return redirect(url_for("auth.register"))

        auth_service.create_user(username=username, email=email, password=password)
        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""

        user = auth_service.verify_login(username=username, password=password)
        if not user:
            flash("Tên người dùng / mật khẩu không đúng hoặc tài khoản bị khóa.", "error")
            return render_template("auth/login.html")

        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role
        flash("Đăng nhập thành công!", "success")
        return redirect(url_for("dashboard.dashboard_home"))

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất thành công!", "info")
    return redirect(url_for("main.index"))


@bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    from ..utils.auth import get_current_user, login_required
    
    user = get_current_user()
    if not user:
        flash("Vui lòng đăng nhập để đổi mật khẩu.", "error")
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not current_password or not new_password or not confirm_password:
            flash("Vui lòng nhập đầy đủ thông tin.", "error")
            return redirect(url_for("auth.change_password"))
        
        if new_password != confirm_password:
            flash("Mật khẩu mới không khớp!", "error")
            return redirect(url_for("auth.change_password"))
        
        # Verify current password
        if not auth_service.verify_login(username=user.username, password=current_password):
            flash("Mật khẩu hiện tại không đúng!", "error")
            return redirect(url_for("auth.change_password"))
        
        # Update password
        auth_service.set_password(user=user, new_password=new_password)
        flash("Đổi mật khẩu thành công!", "success")
        return redirect(url_for("main.profile_dashboard"))
    
    return render_template("auth/change_password.html")

@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Vui lòng nhập email.", "error")
            return redirect(url_for("auth.forgot_password"))

        user = User.query.filter_by(email=email).first()
        if user:
            from flask import current_app
            from itsdangerous import URLSafeTimedSerializer
            
            s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
            token = s.dumps(email, salt="password-reset-salt")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            
            # Trong thực tế sẽ gửi email ở đây.
            # Hiện tại chúng ta giả lập bằng cách in ra log và flash cho người dùng thấy.
            print(f"Password reset link for {email}: {reset_url}")
            flash(f"Yêu cầu đã được gửi! (Trong demo, click vào đây để đặt lại: <a href='{reset_url}'>Đặt lại mật khẩu</a>)", "info")
        else:
            # Luôn báo thành công để tránh lộ thông tin email nào tồn tại (security best practice)
            flash("Nếu email tồn tại trong hệ thống, bạn sẽ nhận được liên kết đặt lại mật khẩu.", "info")
            
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
    
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        # Link hết hạn sau 30 phút (1800 giây)
        email = s.loads(token, salt="password-reset-salt", max_age=1800)
    except (SignatureExpired, BadTimeSignature):
        flash("Liên kết đặt lại mật khẩu đã hết hạn hoặc không hợp lệ.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not new_password or not confirm_password:
            flash("Vui lòng nhập đầy đủ thông tin.", "error")
            return render_template("auth/reset_password.html", token=token)
            
        if new_password != confirm_password:
            flash("Mật khẩu không khớp!", "error")
            return render_template("auth/reset_password.html", token=token)

        user = User.query.filter_by(email=email).first()
        if user:
            auth_service.set_password(user=user, new_password=new_password)
            flash("Đã đặt lại mật khẩu thành công! Vui lòng đăng nhập lại.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Không tìm thấy người dùng.", "error")
            return redirect(url_for("auth.forgot_password"))

    return render_template("auth/reset_password.html", token=token)
