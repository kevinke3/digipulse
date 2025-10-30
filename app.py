from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

# Import your models and config
from models import db, User, Post, Category, Comment, NewsletterSubscription
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file, folder):
    if file and allowed_file(file.filename):
        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > MAX_FILE_SIZE:
            return None, "File size too large. Maximum size is 5MB."
        
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # Ensure upload directory exists
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        
        try:
            # Resize and save image
            image = Image.open(file)
            
            # Set different sizes based on folder
            if folder == 'profiles':
                size = (300, 300)  # Profile pictures
            else:  # posts
                size = (1200, 800)  # Post featured images
            
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            image.save(file_path, 'JPEG', quality=85)
            return filename, None
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return None, "Error processing image."
    
    return None, "Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WEBP."

# Routes
@app.route('/')
def index():
    featured_posts = Post.query.filter_by(is_featured=True, is_published=True).order_by(Post.created_at.desc()).limit(3).all()
    latest_posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).limit(9).all()
    trending_posts = Post.query.filter_by(is_published=True).order_by(Post.views.desc()).limit(6).all()
    categories = Category.query.all()
    return render_template('index.html', 
                         featured_posts=featured_posts,
                         latest_posts=latest_posts,
                         trending_posts=trending_posts,
                         categories=categories)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    return render_template('post.html', post=post)

@app.route('/category/<category_name>')
def category_posts(category_name):
    category = Category.query.filter_by(name=category_name).first_or_404()
    posts = Post.query.filter_by(category_id=category.id, is_published=True).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, category=category)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    posts = Post.query.filter(
        Post.title.ilike(f'%{query}%') | 
        Post.content.ilike(f'%{query}%')
    ).filter_by(is_published=True).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, role='reader')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '':
                filename, error = save_image(file, 'profiles')
                if filename:
                    # Delete old profile picture if it exists and isn't default
                    if current_user.profile_picture and current_user.profile_picture != 'default_profile.png':
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles', current_user.profile_picture)
                        if os.path.exists(old_file_path):
                            try:
                                os.remove(old_file_path)
                            except OSError:
                                pass  # File might not exist
                    
                    current_user.profile_picture = filename
                    flash('Profile picture updated successfully!', 'success')
                elif error:
                    flash(error, 'error')
        
        # Handle bio update
        current_user.bio = request.form.get('bio', '')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role in ['author', 'admin']:
        posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
        return render_template('dashboard.html', posts=posts)
    flash('You do not have permission to access the dashboard.', 'error')
    return redirect(url_for('index'))

@app.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if current_user.role not in ['author', 'admin']:
        flash('You need author privileges to create posts.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        is_featured = bool(request.form.get('is_featured'))
        
        # Handle featured image upload
        featured_image = None
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename != '':
                filename, error = save_image(file, 'posts')
                if filename:
                    featured_image = filename
                    flash('Featured image uploaded successfully!', 'success')
                elif error:
                    flash(error, 'error')
        
        post = Post(
            title=title,
            content=content,
            featured_image=featured_image,
            author_id=current_user.id,
            category_id=category_id,
            is_featured=is_featured,
            is_published=current_user.role == 'admin'  # Auto-publish for admins
        )
        db.session.add(post)
        db.session.commit()
        
        if current_user.role == 'admin':
            flash('Post published successfully!', 'success')
        else:
            flash('Post created successfully! It will be reviewed by an admin before publication.', 'success')
            
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('create_post.html', categories=categories)

@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if user owns the post or is admin
    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to edit this post.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.category_id = request.form.get('category_id')
        post.is_featured = bool(request.form.get('is_featured'))
        post.updated_at = datetime.utcnow()
        
        # Handle featured image upload
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename != '':
                filename, error = save_image(file, 'posts')
                if filename:
                    # Delete old featured image if it exists
                    if post.featured_image:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', post.featured_image)
                        if os.path.exists(old_file_path):
                            try:
                                os.remove(old_file_path)
                            except OSError:
                                pass  # File might not exist
                    
                    post.featured_image = filename
                    flash('Featured image updated successfully!', 'success')
                elif error:
                    flash(error, 'error')
        
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('edit_post.html', post=post, categories=categories)

@app.route('/delete-post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if user owns the post or is admin
    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this post.', 'error')
        return redirect(url_for('dashboard'))
    
    # Delete featured image if it exists
    if post.featured_image:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', post.featured_image)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass  # File might not exist
    
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/publish-post/<int:post_id>', methods=['POST'])
@login_required
def publish_post(post_id):
    if current_user.role != 'admin':
        flash('You do not have permission to publish posts.', 'error')
        return redirect(url_for('dashboard'))
    
    post = Post.query.get_or_404(post_id)
    post.is_published = True
    db.session.commit()
    flash('Post published successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Send email to admin
        try:
            msg = Message(
                subject=f'Contact Form Message from {name}',
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['ADMIN_EMAIL']],
                body=f"Name: {name}\nEmail: {email}\nMessage: {message}"
            )
            mail.send(msg)
            flash('Message sent successfully!', 'success')
        except Exception as e:
            print(f"Email error: {e}")
            flash('Failed to send message. Please try again later.', 'error')
        
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/newsletter', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email')
    if not NewsletterSubscription.query.filter_by(email=email).first():
        subscription = NewsletterSubscription(email=email)
        db.session.add(subscription)
        db.session.commit()
        flash('Successfully subscribed to newsletter!', 'success')
    else:
        flash('Email already subscribed', 'info')
    return redirect(url_for('index'))

@app.route('/like-post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({'likes': post.likes})

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        flash('Comment cannot be empty.', 'error')
    return redirect(url_for('post_detail', post_id=post_id))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        # Create upload directories
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profiles'), exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'posts'), exist_ok=True)
        
        db.create_all()
        # Create default categories
        if not Category.query.first():
            categories = ['Technology', 'Business', 'Lifestyle', 'Entertainment', 'Sports', 'Health', 'Politics']
            for cat_name in categories:
                category = Category(name=cat_name)
                db.session.add(category)
            db.session.commit()
            print("Default categories created!")
        
        # Create admin user if none exists
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@dailypulse.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@dailypulse.com / admin123")
    
    app.run(debug=True)