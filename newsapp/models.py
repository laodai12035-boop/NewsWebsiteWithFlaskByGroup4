from __future__ import annotations

from datetime import datetime

from .extensions import db


class UserRole:
    ADMIN = "admin"
    EDITOR = "editor"
    AUTHOR = "author"
    USER = "user"

    ALL = {ADMIN, EDITOR, AUTHOR, USER}


class ArticleStatus:
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"

    ALL = {DRAFT, PENDING, PUBLISHED, REJECTED, ARCHIVED}


class CommentStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    ALL = {PENDING, APPROVED, REJECTED}


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Mặc định user đăng ký mới là "user" (độc giả),
    # các role admin/editor/author sẽ được gán qua trang quản trị.
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    articles = db.relationship("Article", back_populates="author", lazy=True)
    comments = db.relationship("Comment", back_populates="author", lazy=True)
    favorites = db.relationship("Favorite", back_populates="user", lazy=True)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    articles = db.relationship("Article", back_populates="category", lazy=True)


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    # Can be either an external URL (https://...) or a local static path (uploads/...)
    image_ref = db.Column(db.String(500))

    status = db.Column(db.String(20), nullable=False, default=ArticleStatus.DRAFT, index=True)
    review_note = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime)
    views = db.Column(db.Integer, default=0, nullable=False)

    # AI features
    audio_ref = db.Column(db.String(500))  # static-relative path to generated audio
    audio_duration = db.Column(db.Integer)  # seconds, optional
    summary_text = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)

    author = db.relationship("User", back_populates="articles")
    category = db.relationship("Category", back_populates="articles")
    comments = db.relationship(
        "Comment", back_populates="article", lazy=True, order_by="Comment.created_at.desc()"
    )
    favorites = db.relationship("Favorite", back_populates="article", lazy=True)


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=CommentStatus.PENDING, index=True)
    review_note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    article = db.relationship("Article", back_populates="comments")
    author = db.relationship("User", back_populates="comments")


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    article = db.relationship("Article", back_populates="favorites")
    user = db.relationship("User", back_populates="favorites")

    __table_args__ = (
        db.UniqueConstraint("article_id", "user_id", name="uq_favorites_article_user"),
    )

