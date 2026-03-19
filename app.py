from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news_website.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    articles = db.relationship('Article', backref='author', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    articles = db.relationship('Article', backref='category', lazy=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

# Routes
@app.route('/')
def index():
    articles = Article.query.filter_by(published=True).order_by(Article.created_at.desc()).limit(10).all()
    categories = Category.query.all()
    return render_template('index.html', articles=articles, categories=categories)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    article.views += 1
    db.session.commit()
    return render_template('article_detail.html', article=article)

@app.route('/category/<int:category_id>')
def category_articles(category_id):
    category = Category.query.get_or_404(category_id)
    articles = Article.query.filter_by(category_id=category_id, published=True).order_by(Article.created_at.desc()).all()
    return render_template('category.html', category=category, articles=articles)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Mật khẩu không khớp!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Tên người dùng đã tồn tại!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng!', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất thành công!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để truy cập!', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    articles = Article.query.filter_by(user_id=user.id).order_by(Article.created_at.desc()).all()
    return render_template('dashboard.html', articles=articles, user=user)

@app.route('/dashboard/article/create', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để truy cập!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        article = Article(
            title=request.form.get('title'),
            content=request.form.get('content'),
            excerpt=request.form.get('excerpt'),
            image_url=request.form.get('image_url'),
            user_id=session['user_id'],
            category_id=request.form.get('category_id'),
            published=request.form.get('published') == 'on'
        )
        db.session.add(article)
        db.session.commit()
        flash('Tạo bài viết thành công!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('article_form.html', categories=categories, article=None)

@app.route('/dashboard/article/<int:article_id>/edit', methods=['GET', 'POST'])
def edit_article(article_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để truy cập!', 'error')
        return redirect(url_for('login'))
    
    article = Article.query.get_or_404(article_id)
    
    if article.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Bạn không có quyền chỉnh sửa bài viết này!', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.excerpt = request.form.get('excerpt')
        article.image_url = request.form.get('image_url')
        article.category_id = request.form.get('category_id')
        article.published = request.form.get('published') == 'on'
        article.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Cập nhật bài viết thành công!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('article_form.html', article=article, categories=categories)

@app.route('/dashboard/article/<int:article_id>/delete', methods=['POST'])
def delete_article(article_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để truy cập!', 'error')
        return redirect(url_for('login'))
    
    article = Article.query.get_or_404(article_id)
    
    if article.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Bạn không có quyền xóa bài viết này!', 'error')
        return redirect(url_for('dashboard'))
    
    db.session.delete(article)
    db.session.commit()
    flash('Xóa bài viết thành công!', 'success')
    return redirect(url_for('dashboard'))

# Initialize database and seed data
def init_db():
    with app.app_context():
        db.create_all()
        
        # Check if data already exists
        if User.query.count() == 0:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            
            # Create regular user
            user1 = User(
                username='user1',
                email='user1@example.com',
                password_hash=generate_password_hash('user123')
            )
            db.session.add(user1)
            
            # Create categories
            categories = [
                Category(name='Thời sự', description='Tin tức thời sự trong nước và quốc tế'),
                Category(name='Kinh tế', description='Tin tức về kinh tế, tài chính'),
                Category(name='Văn hóa', description='Tin tức văn hóa, giải trí'),
                Category(name='Thể thao', description='Tin tức thể thao'),
                Category(name='Công nghệ', description='Tin tức công nghệ, khoa học'),
            ]
            for cat in categories:
                db.session.add(cat)
            
            db.session.commit()
            
            # Create sample articles
            articles = [
                Article(
                    title='Xu hướng công nghệ năm 2025',
                    content='Năm 2025 đánh dấu sự phát triển mạnh mẽ của trí tuệ nhân tạo và công nghệ xanh. Các doanh nghiệp đang chuyển đổi số mạnh mẽ, áp dụng AI vào quy trình sản xuất và quản lý. Công nghệ blockchain cũng được ứng dụng rộng rãi trong nhiều lĩnh vực từ tài chính đến y tế.',
                    excerpt='Năm 2025 đánh dấu sự phát triển mạnh mẽ của trí tuệ nhân tạo và công nghệ xanh.',
                    image_url='https://via.placeholder.com/800x400?text=Công+nghệ+2025',
                    user_id=1,
                    category_id=5,
                    published=True
                ),
                Article(
                    title='Giải bóng đá quốc gia khai mạc',
                    content='Giải bóng đá quốc gia 2025 chính thức khai mạc với sự tham gia của 16 đội bóng hàng đầu. Các trận đấu diễn ra tại 8 sân vận động trên toàn quốc. Đây là giải đấu lớn nhất trong năm với sự quan tâm đặc biệt của người hâm mộ.',
                    excerpt='Giải bóng đá quốc gia 2025 chính thức khai mạc với sự tham gia của 16 đội bóng hàng đầu.',
                    image_url='https://via.placeholder.com/800x400?text=Thể+thao',
                    user_id=1,
                    category_id=4,
                    published=True
                ),
                Article(
                    title='Kinh tế phục hồi sau đại dịch',
                    content='Nền kinh tế đang có dấu hiệu phục hồi mạnh mẽ sau thời gian dài chịu ảnh hưởng của đại dịch. GDP tăng trưởng ổn định, xuất khẩu tăng cao, thị trường lao động dần ổn định. Chính phủ đang triển khai nhiều chính sách hỗ trợ doanh nghiệp và người dân.',
                    excerpt='Nền kinh tế đang có dấu hiệu phục hồi mạnh mẽ sau thời gian dài chịu ảnh hưởng của đại dịch.',
                    image_url='https://via.placeholder.com/800x400?text=Kinh+tế',
                    user_id=2,
                    category_id=2,
                    published=True
                ),
                Article(
                    title='Lễ hội văn hóa truyền thống',
                    content='Lễ hội văn hóa truyền thống năm nay được tổ chức quy mô lớn với nhiều hoạt động đặc sắc. Du khách có cơ hội thưởng thức ẩm thực địa phương, xem biểu diễn nghệ thuật dân gian, và tham gia các trò chơi truyền thống. Sự kiện thu hút hàng nghìn lượt khách tham quan.',
                    excerpt='Lễ hội văn hóa truyền thống năm nay được tổ chức quy mô lớn với nhiều hoạt động đặc sắc.',
                    image_url='https://via.placeholder.com/800x400?text=Văn+hóa',
                    user_id=2,
                    category_id=3,
                    published=True
                ),
                Article(
                    title='Hội nghị cấp cao về biến đổi khí hậu',
                    content='Hội nghị cấp cao về biến đổi khí hậu diễn ra với sự tham gia của hơn 100 quốc gia. Các nhà lãnh đạo cam kết giảm phát thải carbon và tăng cường hợp tác quốc tế. Nhiều sáng kiến mới được đề xuất nhằm bảo vệ môi trường và phát triển bền vững.',
                    excerpt='Hội nghị cấp cao về biến đổi khí hậu diễn ra với sự tham gia của hơn 100 quốc gia.',
                    image_url='https://via.placeholder.com/800x400?text=Thời+sự',
                    user_id=1,
                    category_id=1,
                    published=True
                ),
            ]
            
            for article in articles:
                db.session.add(article)
            
            db.session.commit()
            print("Database initialized with seed data!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
