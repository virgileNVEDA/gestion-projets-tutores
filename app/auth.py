from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from .models import User, AcademicSection, AcademicOption, AcademicMention
from .extensions import db
from datetime import datetime
import base64, os, smtplib
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        identifier = request.form.get("email", "").strip()
        email = identifier.lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, active=True).first() or User.query.filter_by(matricule=identifier.upper(), active=True).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash("Connexion réussie. Bienvenue !", "success")
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        error = "Adresse e-mail ou mot de passe incorrect."
    return render_template("auth/login.html", error=error)



@auth_bp.route("/inscription", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    sections = AcademicSection.query.filter_by(active=True).order_by(AcademicSection.name).all()
    if request.method == "POST":
        matricule = request.form.get("matricule", "").strip().upper()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        section_name = request.form.get("section_name", "").strip()
        mention = request.form.get("mention_name", "").strip()
        promotion = request.form.get("promotion", "").strip().upper()
        password = request.form.get("password", "")
        section = AcademicSection.query.filter_by(name=section_name, active=True).first()
        valid_mentions = []
        if section:
            valid_mentions = [m.name for option_item in section.options if option_item.active
                              for m in option_item.mentions if m.active]
        valid_promotions = {"L3", "M2"}
        if (len(full_name) < 3 or not matricule or not email or not section
                or mention not in valid_mentions or promotion not in valid_promotions
                or len(password) < 10):
            flash("Complétez les champs obligatoires. Choisissez une section, une mention correspondante et la promotion L3 ou M2. Le mot de passe doit contenir au moins 10 caractères.", "error")
        elif User.query.filter_by(matricule=matricule).first():
            flash("Ce matricule est déjà associé à un compte. Contactez l'administration.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Cette adresse e-mail est déjà utilisée.", "error")
        else:
            user = User(full_name=full_name, email=email, role="student",
                        matricule=matricule, section_name=section_name,
                        option_name=None, mention_name=mention, mention=mention,
                        promotion=promotion)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Inscription enregistrée. Connectez-vous avec votre adresse e-mail.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", sections=sections)


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="student-password-reset")


@auth_bp.route("/mot-de-passe-oublie", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email, active=True).first()
        flash("Si cette adresse correspond à un compte, un lien de réinitialisation sera envoyé.", "info")
        if user and os.getenv("MAIL_SERVER") and os.getenv("MAIL_USERNAME") and os.getenv("MAIL_PASSWORD"):
            token = _reset_serializer().dumps(user.id)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            message = EmailMessage()
            message["Subject"] = "Réinitialisation de votre mot de passe"
            message["From"] = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME"))
            message["To"] = user.email
            message.set_content("Lien valable 30 minutes : " + reset_url)
            try:
                with smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT", "587")), timeout=15) as smtp:
                    smtp.starttls()
                    smtp.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
                    smtp.send_message(message)
            except Exception:
                current_app.logger.exception("Échec de l'envoi du lien de réinitialisation")
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reinitialiser/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        user_id = _reset_serializer().loads(token, max_age=1800)
    except (BadSignature, SignatureExpired):
        flash("Ce lien est invalide ou expiré. Recommencez la procédure.", "error")
        return redirect(url_for("auth.forgot_password"))
    user = db.session.get(User, user_id)
    if not user or not user.active:
        flash("Compte introuvable ou désactivé.", "error")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 10:
            flash("Le mot de passe doit contenir au moins 10 caractères.", "error")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Mot de passe modifié. Connectez-vous.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")


@auth_bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/profil", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not full_name or not email:
            flash("Le nom complet et l’adresse e-mail sont obligatoires.", "error")
            return redirect(url_for("auth.profile"))
        duplicate = User.query.filter(User.email == email, User.id != current_user.id).first()
        if duplicate:
            flash("Cette adresse e-mail est déjà utilisée par un autre compte.", "error")
            return redirect(url_for("auth.profile"))
        current_user.full_name = full_name
        current_user.email = email
        cropped = request.form.get("profile_photo_cropped", "").strip()
        photo = request.files.get("profile_photo")
        if cropped:
            if not cropped.startswith("data:image/jpeg;base64,") or len(cropped) > 3_000_000:
                flash("Le recadrage de la photo est invalide ou trop volumineux.", "error")
                return redirect(url_for("auth.profile"))
            current_user.profile_photo_data = cropped
        elif photo and photo.filename:
            raw = photo.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                flash("La photo ne doit pas dépasser 2 Mo.", "error")
                return redirect(url_for("auth.profile"))
            mime = photo.mimetype.lower()
            if mime not in {"image/jpeg", "image/png", "image/webp"}:
                flash("Format accepté : JPG, PNG ou WEBP.", "error")
                return redirect(url_for("auth.profile"))
            current_user.profile_photo_data = "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")
        if request.form.get("remove_photo") == "1":
            current_user.profile_photo_data = None
        db.session.commit()
        flash("Votre profil a été mis à jour avec succès.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")


@auth_bp.post("/presence")
@login_required
def update_presence():
    current_user.last_seen_at = datetime.utcnow()
    db.session.commit()
    return {"online": True}, 200
