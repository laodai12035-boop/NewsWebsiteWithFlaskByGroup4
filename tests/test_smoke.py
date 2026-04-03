import unittest

from newsapp import create_app
from newsapp.extensions import db
from newsapp.models import Category, UserRole
from newsapp.services.auth_service import create_user


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLITE_DB_PATH": ":memory:",
                "WTF_CSRF_ENABLED": False,
                "SECRET_KEY": "test",
            },
            seed=False,
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            cat = Category(name="Test", description="Test", active=True)
            db.session.add(cat)
            db.session.commit()
            self.cat_id = cat.id

            create_user("admin", "admin@test.com", "admin123", role=UserRole.ADMIN, active=True)
            create_user("editor", "editor@test.com", "editor123", role=UserRole.EDITOR, active=True)
            create_user("author", "author@test.com", "author123", role=UserRole.AUTHOR, active=True)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login(self, username, password):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def logout(self):
        return self.client.get("/logout", follow_redirects=True)

    def test_author_submit_editor_approve(self):
        # Author submits
        self.login("author", "author123")
        res = self.client.post(
            "/dashboard/articles/create",
            data={
                "title": "Smoke Article",
                "category_id": str(self.cat_id),
                "excerpt": "excerpt",
                "content": "content",
                "action": "submit",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.logout()

        # Editor approves
        self.login("editor", "editor123")
        queue = self.client.get("/editor/review")
        self.assertIn(b"Smoke Article", queue.data)

        # Find article id by simple string search of /article/<id> in HTML is overkill;
        # just approve the first pending by calling service is not accessible here,
        # so we approve via DB.
        with self.app.app_context():
            from newsapp.models import Article, ArticleStatus

            a = Article.query.filter_by(title="Smoke Article", status=ArticleStatus.PENDING).first()
            self.assertIsNotNone(a)
            approve_url = f"/editor/articles/{a.id}/approve"

        res2 = self.client.post(approve_url, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.logout()

        # Public index shows it
        home = self.client.get("/")
        self.assertIn(b"Smoke Article", home.data)


if __name__ == "__main__":
    unittest.main()

