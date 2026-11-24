from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from .models import User
from .extensions import db
from datetime import datetime
import base64

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, active=True).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash("Connexion réussie. Bienvenue !", "success")
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        error = "Adresse e-mail ou mot de passe incorrect."
    return render_template("auth/login.html", error=error)


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("Vous êtes maintenant déconnecté.", "info")
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
        photo = request.files.get("profile_photo")
        if photo and photo.filename:
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
