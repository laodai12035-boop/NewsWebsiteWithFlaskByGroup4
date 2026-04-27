# Website Tin Tức Đời Sống (Flask)

Website tin tức đời sống được xây dựng bằng Flask (Python), HTML/CSS/JavaScript, sử dụng SQLite database.

## 📋 Mô tả dự án

Website tin tức đời sống là một ứng dụng web cho phép:
- Xem các bài viết tin tức theo danh mục
- Đăng ký và đăng nhập tài khoản
- Tìm kiếm / lọc / sắp xếp bài viết
- Author viết bài, lưu nháp, nộp bài chờ duyệt
- Editor duyệt bài (approve/reject), gỡ bài khỏi trang chủ
- Admin quản lý users + phân quyền, CRUD danh mục, backup database

## ✅ Tiến độ hoàn thành

### 1. ✅ Cấu trúc dự án (Layered Architecture)
- Dự án Flask theo hướng MVC/Layered: Controllers (Blueprints) / Services / Models.
- Cấu trúc thư mục:
  ```
  Website tintuc doi song/
  ├── app.py                 # Entrypoint (run server)
  ├── instance/news_website_v2
  ├── newsapp/               # App package (models/services/controllers)
  │   ├── __init__.py        # create_app()
  │   ├── extensions.py      # db
  │   ├── models.py          # User/Category/Article + status/role
  │   ├── seed.py            # seed data (admin/editor/author + demo articles)
  │   ├── controllers/
  │   ├── services/
  │   └── utils/
  ├── templates/             # Thư mục chứa HTML templates
  │   ├── base.html         # Template cơ sở (template inheritance)
  │   ├── index.html        # Trang chủ
  │   ├── login.html        # Trang đăng nhập
  │   ├── register.html     # Trang đăng ký
  │   ├── dashboard_home.html
  │   ├── dashboard_articles.html
  │   ├── editor_review.html
  │   ├── admin_users.html
  │   ├── admin_user_form.html
  │   ├── admin_categories.html
  │   ├── admin_category_form.html
  │   ├── article_detail.html
  │   ├── article_form.html
  │   └── category.html
  ├── static/               # Thư mục chứa CSS, JS, images
  │   ├── css/
  │   │   └── style.css
  │   └── js/
  │       └── main.js
  ├── tests/
  │   └── test_smoke.py      # Test script (unittest)
  ├── requirements.txt      # Dependencies
  └── README.md
  ```

### 2. ✅ Thiết kế giao diện
- **Home**: Hiển thị danh sách bài viết mới nhất và danh mục
- **Login**: Form đăng nhập với validation
- **Register**: Form đăng ký với xác nhận mật khẩu
- **Dashboard**: Quản lý bài viết với bảng thống kê
- **CRUD**: Tạo, đọc, cập nhật, xóa bài viết

### 3. ✅ Giao diện responsive
- Thiết kế responsive cho mobile, tablet, desktop
- Sử dụng CSS Grid và Flexbox
- Menu điều hướng thân thiện với mobile
- Giao diện hiện đại, dễ sử dụng

### 4. ✅ Kết nối Database
- Sử dụng SQLite database (`news_website_v2.db`)
- Kết nối thành công với Flask-SQLAlchemy
- Database tự động tạo khi chạy lần đầu

### 5. ✅ Models Database
Đã tạo 3 bảng dữ liệu chính (trong đó 2 bảng chính phục vụ CRUD nghiệp vụ: `Article`, `Category`):

**User (Người dùng)**
- id, username, email, password_hash
- role: admin/editor/author/user
- active: active/inactive (khóa tài khoản)
- created_at

**Category (Danh mục)**
- id, name, description
- active: active/inactive
- created_at
- Relationship với Article

**Article (Bài viết)**
- id, title, content, excerpt
- image_ref (URL ngoài hoặc `uploads/...` nếu upload)
- status: draft/pending/published/rejected/archived
- review_note (lý do reject)
- created_at, updated_at, published_at, views
- Foreign keys: user_id, category_id

### 6. ✅ Seed Data
- Tự động tạo dữ liệu mẫu khi DB trống:
  - admin/editor/author
  - danh mục mẫu
  - bài demo ở nhiều trạng thái (published/pending/draft)

### 7. ✅ Đăng nhập - Đăng ký
- Đăng ký: Validation username, email, mật khẩu
- Đăng nhập: Xác thực với password hash
- Session management
- Flash messages thông báo
- Bảo mật mật khẩu với Werkzeug

### 8. ✅ Navigation, Header, Footer
- Header: Logo, menu điều hướng, thông tin user
- Footer: Thông tin website, liên kết nhanh, liên hệ
- Menu thống nhất trên tất cả các trang
- Responsive navigation

### 9. ✅ Template Inheritance
- Base template (`base.html`) chứa:
  - Header với navigation
  - Flash messages
  - Footer
  - CSS/JS chung
- Tất cả templates khác extend từ base.html
- Code DRY, dễ bảo trì

### 10. ✅ README.md
- Mô tả đầy đủ dự án
- Hướng dẫn cài đặt và chạy thử
- Liệt kê tiến độ hoàn thành

### 11. ✅ Phân quyền + workflow
- **Admin**: quản lý users + role, CRUD danh mục, backup DB, xem/duyệt/gỡ/xóa bài.
- **Editor**: xem hàng bài pending, approve/reject, gỡ bài.
- **Author**: viết bài, sửa bài của mình khi draft/pending/rejected, nộp bài chờ duyệt; không tự publish.

## 🚀 Hướng dẫn cài đặt và chạy thử

### Yêu cầu hệ thống
- Python 3.7 trở lên
- pip (Python package manager)

### Các bước cài đặt

1. **Cài đặt dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Chạy ứng dụng:**
   ```bash
   python app.py
   ```

3. **Truy cập website:**
   - Mở trình duyệt và truy cập: `http://127.0.0.1:5000`
   - Hoặc: `http://localhost:5000`

### Tài khoản mẫu

Sau khi chạy lần đầu, database sẽ tự động tạo với các tài khoản:

**Admin**
- Username: `admin`
- Password: `admin123`

**Editor**
- Username: `editor`
- Password: `editor123`

**Author**
- Username: `author`
- Password: `author123`

### Tính năng chính

1. **Trang chủ:**
   - Xem danh sách bài viết mới nhất
   - Xem các danh mục tin tức
   - Click vào bài viết để xem chi tiết

2. **Đăng ký/Đăng nhập:**
   - Tạo tài khoản mới
   - Đăng nhập vào hệ thống

3. **Dashboard:**
   - Xem thống kê bài viết
   - Quản lý bài viết của mình
   - Tạo, sửa, xóa bài viết

4. **Tạo bài viết:**
   - Chọn danh mục
   - Nhập tiêu đề, nội dung, tóm tắt
   - Upload ảnh (kiểm tra định dạng/kích thước) hoặc nhập URL ảnh
   - Lưu nháp hoặc nộp bài chờ duyệt

## 🧪 Kiểm thử sơ bộ

Chạy smoke test (unittest):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 📁 Cấu trúc Database

### Bảng User
- `id`: Primary key
- `username`: Tên người dùng (unique)
- `email`: Email (unique)
- `password_hash`: Mật khẩu đã hash
- `created_at`: Ngày tạo
- `is_admin`: Quyền admin

### Bảng Category
- `id`: Primary key
- `name`: Tên danh mục (unique)
- `description`: Mô tả
- `created_at`: Ngày tạo

### Bảng Article
- `id`: Primary key
- `title`: Tiêu đề bài viết
- `content`: Nội dung
- `excerpt`: Tóm tắt
- `image_url`: URL hình ảnh
- `created_at`: Ngày tạo
- `updated_at`: Ngày cập nhật
- `views`: Số lượt xem
- `published`: Trạng thái xuất bản
- `user_id`: Foreign key → User
- `category_id`: Foreign key → Category

## 🛠️ Công nghệ sử dụng

- **Backend:** Flask (Python)
- **Database:** SQLite với SQLAlchemy ORM
- **Frontend:** HTML5, CSS3, JavaScript
- **Security:** Werkzeug password hashing
- **Template Engine:** Jinja2 (Flask)

## 📝 Ghi chú

- Database file (`news_website_v2.db`) sẽ được tạo tự động khi chạy lần đầu
- Seed data sẽ được tạo tự động nếu database trống
- Để reset database, xóa file `news_website_v2.db` và chạy lại

## 🔒 Bảo mật

- Mật khẩu được hash bằng Werkzeug
- Session management cho đăng nhập
- Validation input forms
- CSRF protection (có thể thêm Flask-WTF)

## 📞 Liên hệ

Nếu có thắc mắc hoặc vấn đề, vui lòng liên hệ qua email: contact@tintucdoisong.com

---

**Năm:** 2026
