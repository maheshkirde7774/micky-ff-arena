import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ff_arena import db
from ff_arena.models import User, Notification

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        free_fire_uid = request.form.get('free_fire_uid', '').strip()
        in_game_name = request.form.get('in_game_name', '').strip()

        # Validations
        if not name or not email or not password or not confirm_password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        if not re.match(EMAIL_REGEX, email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please log in.', 'warning')
            return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        if free_fire_uid:
            existing_uid = User.query.filter_by(free_fire_uid=free_fire_uid).first()
            if existing_uid:
                flash('This Free Fire UID is already associated with another account.', 'danger')
                return render_template('register.html', name=name, email=email, free_fire_uid=free_fire_uid, in_game_name=in_game_name)

        # Create user
        new_user = User(
            name=name,
            email=email,
            free_fire_uid=free_fire_uid if free_fire_uid else None,
            in_game_name=in_game_name
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Send welcome notification
        welcome_notif = Notification(
            user_id=new_user.id,
            title='Welcome to Micky FF Arena!',
            message=f'Welcome, {new_user.name}! Your account has been created. Join upcoming tournaments, track your match rooms, and dominate the leaderboard!'
        )
        db.session.add(welcome_notif)
        db.session.commit()

        login_user(new_user)
        flash('Registration successful! Welcome to Micky FF Arena.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('login.html', email=email)

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page and not next_page.startswith('//') and not next_page.startswith('http'):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))
