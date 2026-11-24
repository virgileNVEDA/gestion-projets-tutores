import os
from flask import Flask
from .config import Config
from .extensions import db, login_manager, migrate, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Veuillez vous connecter pour accéder à cet espace."
    login_manager.login_message_category = "info"
    migrate.init_app(app, db)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .auth import auth_bp
    from .main import main_bp
    from .modules import modules_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(modules_bp)

    @app.cli.command("init-db")
    def init_db():
        """Créer les tables et le premier administrateur si les variables sont définies."""
        from .models import User
        db.create_all()
        from sqlalchemy import inspect, text
        columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
        for name, sql_type in (("option_name", "VARCHAR(120)"), ("mention", "VARCHAR(120)"), ("promotion", "VARCHAR(80)")):
            if name not in columns:
                db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {name} {sql_type}'))
        db.session.commit()
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        if email and password and not User.query.filter_by(email=email.lower()).first():
            admin = User(full_name=os.getenv("ADMIN_NAME", "Administrateur"),
                         email=email.lower(), role="admin")
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Administrateur créé : {email}")
        else:
            print("Tables prêtes. Aucun administrateur ajouté (variables absentes ou compte existant).")

    return app
