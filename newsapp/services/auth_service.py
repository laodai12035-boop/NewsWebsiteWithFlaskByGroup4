from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User, UserRole


def create_user(username: str, email: str, password: str, role: str | None = None, active: bool = True) -> User:
    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=generate_password_hash(password),
        # Mặc định user đăng ký mới là độc giả (UserRole.USER).
        role=role or UserRole.USER,
        active=active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def verify_login(username: str, password: str) -> User | None:
    user = User.query.filter_by(username=username.strip()).first()
    if not user:
        return None
    if not user.active:
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user


def set_password(user: User, new_password: str) -> None:
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

