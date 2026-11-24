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
        from .models import User, Institution
        db.create_all()
        from sqlalchemy import inspect, text
        # Ajout idempotent des champs de personnalisation de l'établissement.
        institution_columns = {column["name"] for column in inspect(db.engine).get_columns("institution")}
        institution_additions = {
            "logo_data": "TEXT", "secondary_logo_data": "TEXT", "address": "VARCHAR(300)",
            "phone": "VARCHAR(80)", "contact_email": "VARCHAR(180)", "website": "VARCHAR(240)",
            "motto": "VARCHAR(240)", "academic_year": "VARCHAR(40)", "progress_image_data": "TEXT"
        }
        for name, sql_type in institution_additions.items():
            if name not in institution_columns:
                db.session.execute(text(f'ALTER TABLE "institution" ADD COLUMN {name} {sql_type}'))
        columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
        for name, sql_type in (("option_name", "VARCHAR(120)"), ("mention", "VARCHAR(120)"), ("promotion", "VARCHAR(80)"), ("profile_photo_data", "TEXT"), ("last_seen_at", "TIMESTAMP")):
            if name not in columns:
                db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {name} {sql_type}'))
        # Créer une identité par défaut pour préserver l'installation existante.
        if Institution.query.count() == 0:
            db.session.add(Institution(name=os.getenv("INSTITUTION_NAME", "Établissement académique"),
                                       acronym=os.getenv("INSTITUTION_ACRONYM", "")))
            db.session.commit()
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
