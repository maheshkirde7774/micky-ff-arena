import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True,
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

    # Ensure the instance and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    # Configuration
    db_path = os.path.join(app.instance_path, 'smoke.sqlite3')
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'micky_ff_arena_ultra_secret_key_2026'),
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB max upload
        UPLOAD_FOLDER=uploads_dir
    )

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from ff_arena.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from ff_arena.auth import auth_bp
    from ff_arena.routes import main_bp
    from ff_arena.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Context processors to inject notifications count & active brand info
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        from ff_arena.models import Notification
        unread_notifs = 0
        if current_user.is_authenticated:
            try:
                unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            except Exception:
                unread_notifs = 0
        return {
            'app_name': 'MICKY FF ARENA',
            'tagline': 'JOIN • COMPETE • WIN',
            'unread_notifications_count': unread_notifs
        }

    return app
