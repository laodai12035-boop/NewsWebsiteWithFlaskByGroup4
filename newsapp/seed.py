from __future__ import annotations

from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Article, ArticleStatus, Category, User, UserRole


def seed_if_empty() -> None:
    """Seed minimal demo data if the DB is empty.

    Only runs when there are no users yet.
    """
    if User.query.count() > 0:
        return

    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123"),
        role=UserRole.ADMIN,
        active=True,
    )
    editor = User(
        username="editor",
        email="editor@example.com",
        password_hash=generate_password_hash("editor123"),
        role=UserRole.EDITOR,
        active=True,
    )
    author = User(
        username="author",
        email="author@example.com",
        password_hash=generate_password_hash("author123"),
        role=UserRole.AUTHOR,
        active=True,
    )
    db.session.add_all([admin, editor, author])
    db.session.commit()

    categories = [
        Category(name="Thời sự", description="Tin tức thời sự trong nước và quốc tế", active=True),
        Category(name="Kinh tế", description="Tin tức về kinh tế, tài chính", active=True),
        Category(name="Văn hóa", description="Tin tức văn hóa, giải trí", active=True),
        Category(name="Thể thao", description="Tin tức thể thao", active=True),
        Category(name="Công nghệ", description="Tin tức công nghệ, khoa học", active=True),
    ]
    db.session.add_all(categories)
    db.session.commit()

    articles = [
        Article(
            title="Bài đã xuất bản (demo)",
            excerpt="Đây là bài viết đã được duyệt và xuất bản để hiển thị trên trang chủ.",
            content="Nội dung demo. Bạn có thể đăng nhập bằng editor để duyệt bài pending, hoặc author để nộp bài.",
            image_ref="https://via.placeholder.com/800x400?text=Published",
            status=ArticleStatus.PUBLISHED,
            user_id=author.id,
            category_id=categories[0].id,
        ),
        Article(
            title="Bài chờ duyệt (demo)",
            excerpt="Bài này đang ở trạng thái pending và sẽ xuất hiện trong hàng duyệt của Editor.",
            content="Nội dung demo pending.",
            image_ref="https://via.placeholder.com/800x400?text=Pending",
            status=ArticleStatus.PENDING,
            user_id=author.id,
            category_id=categories[1].id,
        ),
        Article(
            title="Bài nháp (demo)",
            excerpt="Bài này là draft của tác giả.",
            content="Nội dung demo draft.",
            image_ref="https://via.placeholder.com/800x400?text=Draft",
            status=ArticleStatus.DRAFT,
            user_id=author.id,
            category_id=categories[2].id,
        ),
    ]
    db.session.add_all(articles)
    db.session.commit()

