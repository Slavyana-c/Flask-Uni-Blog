# views.py, implemented by following the tutorials from:
# Flask Web Development by Miguel Grinberg (First Edition) and
# Flask Tutorials by Corey Schafer
# (online) https://www.youtube.com/playlist?list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH

import os
import binascii
import logging
from PIL import Image
from app import app, mail, db, bcrypt, logger
from flask import abort, render_template, request, flash, redirect, url_for
from .forms import RegistrationForm, PostForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm
from .models import User, Post, Follow
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

# Home page
@app.route('/')
@app.route('/home')
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)

# About page
@app.route('/about')
def about():
    return render_template('about.html', title='About')

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        logger.info('User already has a registration.')
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        logger.info('New registered user: {} - {}'.format(user.email, user.username))
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                logger.info('User logged in: {} - {}'.format(user.email, user.username))
                return redirect(next_page) if next_page else redirect(url_for('index'))

            else:
                flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

# Logout
@app.route('/logout')
@login_required
def logout():
    logger.info('Logging out: {} - {}'.format(current_user.email, current_user.username))
    logout_user()
    return redirect(url_for('index'))

# Hash and save picture
def save_picture(form_picture):
    random_hex = binascii.b2a_hex(os.urandom(8))
    _, file_extension = os.path.splitext(form_picture.filename)
    picture_file_name = random_hex.decode() + file_extension
    print(picture_file_name)
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_file_name)

    output_size = (250, 250)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_file_name

# User account page
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        logger.info('Changed account details for {} - {}'.format(current_user.email, current_user.username))
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.profile_image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('account.html', title='Account', profile_image=profile_image, form=form)

# New post page
@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post=Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        logger.info('New post created: {} by {}'.format(post.title, post.author))
        return redirect(url_for('index'))
    return render_template('create_post.html', title='New Post', form=form, page='New Post')

# Single post view
@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

# Update post
@app.route('/post/<int:post_id>/update',  methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        logger.error('User tried to update a post of someone else. Access denied.')
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been successfully updated!', 'success')
        logger.info('Post updated: {} by {}'.format(post.title, post.author))
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, page='Update Post')

# Delete post
@app.route('/post/<int:post_id>/delete',  methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been successfully deleted!', 'success')
    return redirect(url_for('index'))

# Posts by followed users
@app.route('/posts_followed')
@login_required
def posts_followed():
    page = request.args.get('page', 1, type=int)
    current_id = current_user.id
    posts = Post.query.join(Follow, Follow.followed_id == Post.user_id)\
    .filter(Follow.follower_id == current_id )\
    .order_by(Post.date_posted.desc())\
    .paginate(page=page, per_page=5)

    return render_template('followed_posts.html', posts=posts)

# Follow user
@app.route("/follow/<string:username>")
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'danger')
        return redirect(url_for('index'))
    if current_user.is_following(user):
        flash('You are already following this user.', 'info')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username, 'success')
    db.session.commit()
    return redirect(url_for('user_posts', username=username))

# Unfollow user
@app.route("/unfollow/<string:username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'danger')
        return redirect(url_for('index'))
    if current_user.is_following(user):
        current_user.unfollow(user)
        flash('You have unfollowed %s.' % username, 'success')
        db.session.commit()
        return redirect(url_for('user_posts', username=username))

    flash('You are not following this user.', 'info')
    return redirect(url_for('user_posts', username=username))

# Posts by a single user
@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

# Send an email with reset password instructions
def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body =  "To reset your password, please use the following link: %s\n" %url_for('reset_token', token=token, _external=True)
    mail.send(msg)

# Input email for reset password page
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        logger.info('Reset token sent to {}.'.format(user.email))
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

# Page to reset password
@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_token(token)
    if not user:
        flash('This token is invalid or expired.', 'warning')
        logger.warning('Invalid or expired token.')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated!', 'success')
        logger.info('Updated password for: {} - {}.'.format(user.email, user.username))
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
