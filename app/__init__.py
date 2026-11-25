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


    @app.context_processor
    def inject_global_template_context():
        from datetime import datetime
        from .models import Institution
        return {"institution": Institution.query.order_by(Institution.id.asc()).first(), "now": datetime.utcnow()}

    from . import models  # noqa: F401
    from .auth import auth_bp
    from .main import main_bp
    from .modules import modules_bp, generate_matricule
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(modules_bp)

    @app.cli.command("init-db")
    def init_db():
        """Créer les tables et le premier administrateur si les variables sont définies."""
        from .models import User, Institution, AcademicSection, AcademicOption
        db.create_all()
        from sqlalchemy import inspect, text
        # Ajout idempotent des champs de personnalisation de l'établissement.
        institution_columns = {column["name"] for column in inspect(db.engine).get_columns("institution")}
        institution_additions = {
            "logo_data": "TEXT", "secondary_logo_data": "TEXT", "address": "VARCHAR(300)",
            "phone": "VARCHAR(80)", "contact_email": "VARCHAR(180)", "website": "VARCHAR(240)",
            "motto": "VARCHAR(240)", "academic_year": "VARCHAR(40)", "progress_image_data": "TEXT", "promotions_json": "TEXT"
        }
        for name, sql_type in institution_additions.items():
            if name not in institution_columns:
                db.session.execute(text(f'ALTER TABLE "institution" ADD COLUMN {name} {sql_type}'))
        columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
        for name, sql_type in (("phone", "VARCHAR(40)"), ("option_name", "VARCHAR(120)"), ("section_name", "VARCHAR(120)"), ("mention_name", "VARCHAR(120)"), ("mention", "VARCHAR(120)"), ("promotion", "VARCHAR(80)"), ("profile_photo_data", "TEXT"), ("last_seen_at", "TIMESTAMP"), ("section_id", "INTEGER"), ("option_id", "INTEGER"), ("mention_id", "INTEGER")):
            if name not in columns:
                db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {name} {sql_type}'))
        section = AcademicSection.query.filter_by(name="Sciences commerciales").first()
        if section is None:
            section = AcademicSection(name="Sciences commerciales")
            db.session.add(section)
            db.session.flush()
        # Référentiel désormais présenté comme Section -> Mention -> Promotion.
        mention_names = ["Banque, Microfinance et Assurance (BMA)", "Marketing", "Comptabilité et Finance", "Administration et Gestion des Ressources Humaines (AGRH)", "Logistique", "Fiscalité", "Entrepreneuriat"]
        existing_mentions = {item.name.strip().casefold() for item in AcademicOption.query.filter_by(section_id=section.id).all()}
        for mention_name in mention_names:
            if mention_name.strip().casefold() not in existing_mentions:
                db.session.add(AcademicOption(section_id=section.id, name=mention_name))
                existing_mentions.add(mention_name.strip().casefold())
        db.session.commit()
        # Créer une identité par défaut pour préserver l'installation existante.
        if Institution.query.count() == 0:
            db.session.add(Institution(name=os.getenv("INSTITUTION_NAME", "Établissement académique"),
                                       acronym=os.getenv("INSTITUTION_ACRONYM", "")))
            db.session.commit()
        institution = Institution.query.order_by(Institution.id.asc()).first()
        if institution and not institution.promotions_json:
            import json
            institution.promotions_json = json.dumps(["L3", "M2"], ensure_ascii=False)
            db.session.commit()
        # Harmoniser les matricules existants : identifiant court lié au rôle et aux initiales.
        from .models import ROLES
        for account in User.query.order_by(User.id.asc()).all():
            expected_prefix = {"student":"ET","tutor":"DIR","admin":"ADM"}.get(account.role, "USR")
            if account.role != "student" and (not account.matricule or not account.matricule.startswith(expected_prefix + "-")):
                account.matricule = generate_matricule(account.full_name, account.role, exclude_user_id=account.id)
        db.session.commit()
        db.session.execute(text('UPDATE "user" SET role = \'admin\' WHERE role IN (\'section_head\', \'department_head\', \'coordination\')'))
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
