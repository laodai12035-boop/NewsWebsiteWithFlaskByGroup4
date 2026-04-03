from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, cast

from flask import flash, g, redirect, session, url_for

from ..models import User, UserRole
from ..extensions import db

F = TypeVar("F", bound=Callable[..., object])


def get_current_user() -> User | None:
    """Returns the current logged-in user or None.

    Cached in Flask `g` for the request to avoid repeated DB queries.
    """
    if hasattr(g, "current_user"):
        return cast(User | None, g.current_user)

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return None

    user = db.session.get(User, int(user_id))
    g.current_user = user
    return user


def login_required(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Vui lòng đăng nhập để truy cập!", "error")
            return redirect(url_for("auth.login"))
        if not user.active:
            session.clear()
            flash("Tài khoản đang bị khóa / không hoạt động.", "error")
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return cast(F, wrapper)


def roles_required(*roles: str) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Vui lòng đăng nhập để truy cập!", "error")
                return redirect(url_for("auth.login"))
            if not user.active:
                session.clear()
                flash("Tài khoản đang bị khóa / không hoạt động.", "error")
                return redirect(url_for("auth.login"))
            if user.role not in roles:
                flash("Bạn không có quyền truy cập chức năng này.", "error")
                return redirect(url_for("main.index"))
            return fn(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def is_admin(user: User | None) -> bool:
    return bool(user and user.role == UserRole.ADMIN)

