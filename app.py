from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from datetime import datetime
import os
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
        Post.content.ilike(f'%{query}%'),
        Post.is_published=True
    ).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, role='reader')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role in ['author', 'admin']:
        posts = Post.query.filter_by(author_id=current_user.id).all()
        return render_template('dashboard.html', posts=posts)
    return redirect(url_for('index'))

@app.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if current_user.role not in ['author', 'admin']:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        is_featured = bool(request.form.get('is_featured'))
        
        post = Post(
            title=title,
            content=content,
            author_id=current_user.id,
            category_id=category_id,
            is_featured=is_featured,
            is_published=current_user.role == 'admin'
        )
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('create_post.html', categories=categories)

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
        msg = Message(
            subject=f'Contact Form Message from {name}',
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[app.config['ADMIN_EMAIL']],
            body=f"Name: {name}\nEmail: {email}\nMessage: {message}"
        )
        mail.send(msg)
        flash('Message sent successfully!')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/newsletter', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email')
    if not NewsletterSubscription.query.filter_by(email=email).first():
        subscription = NewsletterSubscription(email=email)
        db.session.add(subscription)
        db.session.commit()
        flash('Successfully subscribed to newsletter!')
    else:
        flash('Email already subscribed')
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
    comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    flash('Comment added successfully!')
    return redirect(url_for('post_detail', post_id=post_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default categories
        if not Category.query.first():
            categories = ['Technology', 'Business', 'Lifestyle', 'Entertainment', 'Sports', 'Health', 'Politics']
            for cat_name in categories:
                category = Category(name=cat_name)
                db.session.add(category)
            db.session.commit()
    app.run(debug=True)