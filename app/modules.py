import os
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from .extensions import db
from .models import User, AcademicProgram, ProjectTopic, WorkflowEvent, Message, DocumentVersion, Meeting, Notification, Institution, ROLES, AcademicSection, AcademicOption, AcademicMention

modules_bp = Blueprint("modules", __name__, url_prefix="/modules")
ALLOWED = {"pdf", "doc", "docx", "odt", "xlsx", "pptx", "png", "jpg", "jpeg"}

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco

ROLE_MATRICULE_PREFIX = {
    "student": "ET", "tutor": "DIR", "admin": "ADM"
}

def generate_matricule(full_name, role, exclude_user_id=None):
    """Identifiant court : préfixe du rôle + initiales + compteur unique."""
    import re
    import unicodedata
    words = [w for w in re.split(r"[^A-Za-zÀ-ÿ0-9]+", (full_name or "").strip()) if w]
    chosen = [words[0], words[-1]] if len(words) > 1 else words
    initials = "".join(unicodedata.normalize("NFKD", w[0]).encode("ascii", "ignore").decode().upper() for w in chosen)
    initials = (initials or "XX")[:2]
    base = f"{ROLE_MATRICULE_PREFIX.get(role, 'USR')}-{initials}"
    number = 1
    while True:
        candidate = f"{base}-{number:03d}"
        query = User.query.filter_by(matricule=candidate)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        if query.first() is None:
            return candidate
        number += 1
def visible_topics():
    q = ProjectTopic.query
    if current_user.role == "student": q = q.filter_by(student_id=current_user.id)
    elif current_user.role == "tutor": q = q.filter_by(tutor_id=current_user.id)
    elif current_user.role == "codirector": q = q.filter_by(codirector_id=current_user.id)
    return q.order_by(ProjectTopic.updated_at.desc())

def can_access(topic):
    if current_user.role == "admin": return True
    return current_user.id in {topic.student_id, topic.tutor_id, topic.codirector_id}

def notify(user_id, topic_id, title, body):
    if user_id and user_id != current_user.id:
        db.session.add(Notification(user_id=user_id, topic_id=topic_id, title=title, body=body))


@modules_bp.app_context_processor
def inject_institution():
    return {"institution": Institution.query.order_by(Institution.id.asc()).first()}

def _image_data(file, label):
    if not file or not file.filename:
        return None
    import base64
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    mime = {"png":"image/png", "jpg":"image/jpeg", "jpeg":"image/jpeg", "webp":"image/webp"}.get(ext)
    if not mime:
        raise ValueError(f"{label} : format accepté PNG, JPG ou WEBP.")
    raw = file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError(f"{label} : chaque image doit faire 2 Mo maximum.")
    if not raw:
        raise ValueError(f"{label} : fichier vide.")
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")

@modules_bp.route("/parametres", methods=["GET", "POST"])
@login_required
def settings():
    if current_user.role != "admin":
        abort(403)
    institution = Institution.query.order_by(Institution.id.asc()).first()
    if institution is None:
        institution = Institution(name="Établissement académique")
        db.session.add(institution)
        db.session.commit()
    import json
    try:
        promotions = json.loads(institution.promotions_json or '["L3","M2"]')
        if not isinstance(promotions, list): promotions = ["L3", "M2"]
    except (ValueError, TypeError):
        promotions = ["L3", "M2"]
    promotions = list(dict.fromkeys(str(x).strip() for x in promotions if str(x).strip()))
    for required in ("L3", "M2"):
        if required not in promotions: promotions.append(required)
    if request.method == "POST":
        try:
            institution.name = request.form.get("institution_name", "").strip() or institution.name
            institution.acronym = request.form.get("acronym", "").strip() or None
            institution.address = request.form.get("address", "").strip() or None
            institution.phone = request.form.get("phone", "").strip() or None
            institution.contact_email = request.form.get("contact_email", "").strip() or None
            institution.website = request.form.get("website", "").strip() or None
            institution.motto = request.form.get("motto", "").strip() or None
            institution.academic_year = request.form.get("academic_year", "").strip() or None
            raw_promotions = request.form.get("promotions", "")
            promotion_items = list(dict.fromkeys(line.strip() for line in raw_promotions.replace(",", "\n").splitlines() if line.strip()))
            for required in ("L3", "M2"):
                if required not in promotion_items: promotion_items.append(required)
            if len(promotion_items) > 50: raise ValueError("Vous pouvez configurer au maximum 50 promotions.")
            if any(len(item) > 80 for item in promotion_items): raise ValueError("Chaque promotion doit contenir au maximum 80 caractères.")
            institution.promotions_json = json.dumps(promotion_items, ensure_ascii=False)
            institution.primary_color = request.form.get("primary_color", "#142D49")
            institution.accent_color = request.form.get("accent_color", "#079B83")
            institution.progress_enabled = request.form.get("progress_enabled") == "on"
            institution.progress_color = request.form.get("progress_color", "#079B83")
            for field, attr, label in [
                ("logo_file", "logo_data", "Logo principal"),
                ("secondary_logo_file", "secondary_logo_data", "Deuxième logo"),
                ("progress_image_file", "progress_image_data", "Image de chargement")
            ]:
                uploaded = request.files.get(field)
                if uploaded and uploaded.filename:
                    setattr(institution, attr, _image_data(uploaded, label))
            if request.form.get("remove_logo") == "on": institution.logo_data = None
            if request.form.get("remove_secondary_logo") == "on": institution.secondary_logo_data = None
            if request.form.get("remove_progress_image") == "on": institution.progress_image_data = None
            import json
            images = json.loads(institution.carousel_images or "[]")
            if request.form.get("clear_carousel") == "on": images = []
            for uploaded in request.files.getlist("carousel_files"):
                if uploaded and uploaded.filename:
                    if len(images) >= 12: raise ValueError("Le carrousel accepte au maximum 12 images.")
                    images.append(_image_data(uploaded, "Image du carrousel"))
            if len(images) > 12: raise ValueError("Le carrousel accepte au maximum 12 images.")
            # Les anciennes adresses web restent compatibles.
            institution.carousel_images = json.dumps(images, ensure_ascii=False)
            db.session.commit()
            flash("Les paramètres de l’établissement ont été enregistrés.", "success")
            return redirect(url_for("modules.settings"))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    import json
    try:
        promotions = json.loads(institution.promotions_json or '["L3","M2"]')
    except (ValueError, TypeError):
        promotions = ["L3", "M2"]
    promotions = list(dict.fromkeys(str(x).strip() for x in promotions if str(x).strip()))
    for required in ("L3", "M2"):
        if required not in promotions: promotions.append(required)
    try:
        carousel_images = json.loads(institution.carousel_images or "[]")
    except (ValueError, TypeError):
        carousel_images = []
    return render_template("settings.html", institution=institution, carousel_images=carousel_images, promotions=promotions)


@modules_bp.get("/api/sections")
def api_sections():
    return jsonify([{"id":s.id,"name":s.name} for s in AcademicSection.query.filter_by(active=True).order_by(AcademicSection.name).all()])


@modules_bp.get("/api/sections/<int:section_id>/options")
def api_options(section_id):
    return jsonify([{"id":o.id,"name":o.name} for o in AcademicOption.query.filter_by(section_id=section_id,active=True).order_by(AcademicOption.name).all()])


@modules_bp.get("/api/options/<int:option_id>/mentions")
def api_mentions(option_id):
    return jsonify([{"id":m.id,"name":m.name} for m in AcademicMention.query.filter_by(option_id=option_id,active=True).order_by(AcademicMention.name).all()])

@modules_bp.get("/api/sections/<int:section_id>/mentions")
def api_section_mentions(section_id):
    section_item = AcademicSection.query.filter_by(id=section_id, active=True).first_or_404()
    mentions = AcademicOption.query.filter_by(section_id=section_item.id, active=True).order_by(AcademicOption.name).all()
    return jsonify([{"id": item.id, "name": item.name} for item in mentions])


@modules_bp.route("/<section>", methods=["GET","POST"])
@login_required
def section(section):
    allowed = {"etudiants","enseignants","programmes","sujets","encadrement","validations","messagerie","documents","reunions","rapports","notifications","utilisateurs"}
    if section not in allowed: abort(404)
    admin_sections = {"etudiants","enseignants","programmes","utilisateurs"}
    if section in admin_sections and current_user.role != "admin": abort(403)
    if section == "rapports" and current_user.role != "admin": abort(403)

    if request.method == "POST":
        action = request.form.get("action","")
        try:
            if action == "create_section" and current_user.role == "admin":
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom de la section est obligatoire.")
                if AcademicSection.query.filter_by(name=name).first(): raise ValueError("Cette section existe déjà.")
                db.session.add(AcademicSection(name=name))
                flash("Section ajoutée.","success")
            elif action in {"create_option", "create_mention"} and current_user.role == "admin":
                parent=AcademicSection.query.get_or_404(int(request.form.get("section_id")))
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom de la mention est obligatoire.")
                duplicate=AcademicOption.query.filter(AcademicOption.section_id==parent.id,db.func.lower(AcademicOption.name)==name.lower()).first()
                if duplicate: raise ValueError("Cette mention existe déjà dans cette section.")
                db.session.add(AcademicOption(section_id=parent.id,name=name))
                flash("Mention ajoutée à la section.","success")
            elif action == "edit_section" and current_user.role == "admin":
                item=AcademicSection.query.get_or_404(int(request.form.get("section_id")))
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom de la section est obligatoire.")
                duplicate=AcademicSection.query.filter(AcademicSection.name==name,AcademicSection.id!=item.id).first()
                if duplicate: raise ValueError("Cette section existe déjà.")
                item.name=name
                flash("Section modifiée.","success")
            elif action == "edit_option" and current_user.role == "admin":
                item=AcademicOption.query.get_or_404(int(request.form.get("option_id")))
                parent=AcademicSection.query.get_or_404(int(request.form.get("section_id")))
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom de la mention est obligatoire.")
                duplicate=AcademicOption.query.filter(AcademicOption.section_id==parent.id,db.func.lower(AcademicOption.name)==name.lower(),AcademicOption.id!=item.id).first()
                if duplicate: raise ValueError("Cette mention existe déjà dans cette section.")
                item.section_id=parent.id; item.name=name
                flash("Mention modifiée.","success")
            elif action == "edit_mention" and current_user.role == "admin":
                item=AcademicMention.query.get_or_404(int(request.form.get("mention_id")))
                parent=AcademicOption.query.get_or_404(int(request.form.get("option_id")))
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom de la mention est obligatoire.")
                duplicate=AcademicMention.query.filter(AcademicMention.option_id==parent.id,AcademicMention.name==name,AcademicMention.id!=item.id).first()
                if duplicate: raise ValueError("Cette mention existe déjà dans cette option.")
                item.option_id=parent.id; item.name=name
                flash("Mention modifiée.","success")
            elif action == "toggle_academic_item" and current_user.role == "admin":
                kind=request.form.get("kind")
                item_id=int(request.form.get("item_id"))
                model={"section":AcademicSection,"option":AcademicOption,"mention":AcademicMention}.get(kind)
                if not model: raise ValueError("Type de référence invalide.")
                item=model.query.get_or_404(item_id)
                item.active=not item.active
                flash("Élément activé." if item.active else "Élément désactivé.","success")
            elif action == "create_user" and current_user.role == "admin":
                email=request.form.get("email","").strip().lower()
                if User.query.filter_by(email=email).first(): raise ValueError("Cette adresse e-mail existe déjà.")
                role=request.form.get("role","student")
                if role not in ROLES: raise ValueError("Rôle invalide.")
                section_name=request.form.get("section_name","").strip()
                mention_name=request.form.get("mention_name","").strip()
                matricule=request.form.get("matricule","").strip().upper()
                if role in {"student","tutor"}:
                    if role=="student" and not matricule: raise ValueError("Le matricule officiel de l’étudiant est obligatoire.")
                    if role=="student" and User.query.filter_by(matricule=matricule).first(): raise ValueError("Ce matricule est déjà utilisé.")
                    parent=AcademicSection.query.filter_by(name=section_name,active=True).first()
                    men=AcademicOption.query.filter_by(name=mention_name,active=True,section_id=parent.id).first() if parent and mention_name else None
                    if not parent or not men or not request.form.get("promotion","").strip(): raise ValueError("Pour un étudiant ou un tuteur, la section, la mention et la promotion sont obligatoires et doivent respecter leur rattachement.")
                user=User(full_name=request.form.get("full_name","").strip(),email=email,phone=request.form.get("phone","").strip() or None,role=role,section_name=section_name or None,option_name=None,mention_name=mention_name or None,mention=mention_name or None,promotion=request.form.get("promotion","").strip() or None)
                password=request.form.get("password","")
                if len(user.full_name)<3 or len(password)<10: raise ValueError("Nom obligatoire et mot de passe de 10 caractères minimum.")
                user.set_password(password); db.session.add(user); db.session.flush()
                user.matricule = matricule if role=="student" else generate_matricule(user.full_name, role)
                db.session.commit()
                flash(f"Compte créé avec succès. Matricule : {user.matricule}" if role == "student" else "Compte créé avec succès.", "success")
            elif action == "create_program" and current_user.role == "admin":
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom du programme est obligatoire.")
                db.session.add(AcademicProgram(name=name,level=request.form.get("level","").strip()))
                flash("Programme ajouté.","success")
            elif action == "create_topic":
                student_id=current_user.id if current_user.role=="student" else int(request.form.get("student_id"))
                student=User.query.get_or_404(student_id)
                if current_user.role=="student" and ProjectTopic.query.filter_by(student_id=current_user.id).filter(ProjectTopic.status!="rejected").first():
                    raise ValueError("Un dossier actif existe déjà dans votre espace. Contactez l'administration pour une nouvelle soumission.")
                topic=ProjectTopic(title=request.form.get("title","").strip(),problem_statement=request.form.get("problem_statement","").strip(),objectives=request.form.get("objectives","").strip(),methodology=request.form.get("methodology","").strip(),keywords=request.form.get("keywords","").strip(),student_id=student.id,program_id=int(request.form.get("program_id")) if request.form.get("program_id") else None,status="submitted" if current_user.role=="student" else "draft")
                if len(topic.title)<12: raise ValueError("Le titre doit contenir au moins 12 caractères.")
                db.session.add(topic); db.session.flush()
                db.session.add(WorkflowEvent(topic_id=topic.id,actor_id=current_user.id,action="Soumission du sujet" if topic.status=="submitted" else "Création du dossier"))
                flash("Sujet enregistré.","success")
            elif action == "edit_topic":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                if not can_access(topic): abort(403)
                if current_user.role not in {"admin"} and not (current_user.role=="student" and topic.student_id==current_user.id and topic.status in {"draft","revision","rejected"}):
                    abort(403)
                title=request.form.get("title","").strip()
                if len(title)<12: raise ValueError("Le titre doit contenir au moins 12 caractères.")
                topic.title=title
                topic.problem_statement=request.form.get("problem_statement","").strip()
                topic.objectives=request.form.get("objectives","").strip()
                topic.methodology=request.form.get("methodology","").strip()
                topic.keywords=request.form.get("keywords","").strip()
                topic.program_id=int(request.form.get("program_id")) if request.form.get("program_id") else None
                topic.updated_at=datetime.utcnow()
                db.session.add(WorkflowEvent(topic_id=topic.id,actor_id=current_user.id,action="Modification du sujet"))
                notify(topic.student_id,topic.id,"Sujet modifié",topic.title)
                flash("Le sujet a été modifié.","success")
            elif action == "delete_topic" and current_user.role=="admin":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                # Nettoyage explicite des éléments liés avant suppression du dossier.
                Notification.query.filter_by(topic_id=topic.id).delete(synchronize_session=False)
                Message.query.filter_by(topic_id=topic.id).delete(synchronize_session=False)
                Meeting.query.filter_by(topic_id=topic.id).delete(synchronize_session=False)
                DocumentVersion.query.filter_by(topic_id=topic.id).delete(synchronize_session=False)
                WorkflowEvent.query.filter_by(topic_id=topic.id).delete(synchronize_session=False)
                db.session.delete(topic)
                flash("Le dossier et son historique ont été supprimés.","success")
            elif action == "edit_user" and current_user.role=="admin":
                user=User.query.get_or_404(int(request.form.get("user_id")))
                full_name=request.form.get("full_name","").strip()
                email=request.form.get("email","").strip().lower()
                if len(full_name)<3 or not email: raise ValueError("Nom et adresse e-mail valides obligatoires.")
                if User.query.filter(User.email==email,User.id!=user.id).first(): raise ValueError("Cette adresse e-mail est déjà utilisée.")
                role=request.form.get("role",user.role)
                if role not in ROLES: raise ValueError("Rôle invalide.")
                if user.id==current_user.id and role!="admin": raise ValueError("Vous ne pouvez pas retirer votre propre rôle administrateur.")
                old_role=user.role
                user.full_name=full_name; user.email=email; user.phone=request.form.get("phone","").strip() or None; user.role=role
                if role=="student":
                    new_matricule=request.form.get("matricule",user.matricule or "").strip().upper()
                    duplicate=User.query.filter(User.matricule==new_matricule,User.id!=user.id).first()
                    if not new_matricule or duplicate: raise ValueError("Le matricule étudiant est obligatoire et doit être unique.")
                    user.matricule=new_matricule
                elif old_role != role or not user.matricule:
                    user.matricule=generate_matricule(full_name, role, exclude_user_id=user.id)
                section_name=request.form.get("section_name","").strip()
                mention_name=request.form.get("mention_name","").strip()
                if role in {"student","tutor"}:
                    parent=AcademicSection.query.filter_by(name=section_name,active=True).first()
                    men=AcademicOption.query.filter_by(name=mention_name,active=True,section_id=parent.id).first() if parent and mention_name else None
                    if not parent or not men or not request.form.get("promotion","").strip(): raise ValueError("Pour un étudiant ou un tuteur, la section, la mention et la promotion sont obligatoires et doivent respecter leur rattachement.")
                user.section_name=section_name or None
                user.option_name=None
                user.mention_name=mention_name or None
                user.mention=mention_name or None
                user.promotion=request.form.get("promotion","").strip() or None
                if request.form.get("password",""):
                    if len(request.form["password"])<10: raise ValueError("Le mot de passe doit contenir au moins 10 caractères.")
                    user.set_password(request.form["password"])
                flash("Le compte a été modifié.","success")
            elif action == "delete_user" and current_user.role=="admin":
                user=User.query.get_or_404(int(request.form.get("user_id")))
                if user.id==current_user.id: raise ValueError("Vous ne pouvez pas supprimer votre propre compte.")
                linked=ProjectTopic.query.filter((ProjectTopic.student_id==user.id)|(ProjectTopic.tutor_id==user.id)|(ProjectTopic.codirector_id==user.id)).first()
                if linked: raise ValueError("Ce compte est lié à un dossier académique. Désactivez-le au lieu de le supprimer.")
                if Notification.query.filter_by(user_id=user.id).first() or DocumentVersion.query.filter_by(uploader_id=user.id).first() or Message.query.filter_by(sender_id=user.id).first() or Meeting.query.filter_by(organizer_id=user.id).first() or WorkflowEvent.query.filter_by(actor_id=user.id).first():
                    raise ValueError("Ce compte possède un historique. La suppression est bloquée pour préserver la traçabilité.")
                db.session.delete(user); flash("Le compte a été supprimé.","success")
            elif action == "edit_program" and current_user.role=="admin":
                program=AcademicProgram.query.get_or_404(int(request.form.get("program_id")))
                name=request.form.get("name","").strip()
                if not name: raise ValueError("Le nom du programme est obligatoire.")
                program.name=name; program.level=request.form.get("level","").strip() or None
                flash("Le programme a été modifié.","success")
            elif action == "delete_program" and current_user.role=="admin":
                program=AcademicProgram.query.get_or_404(int(request.form.get("program_id")))
                if ProjectTopic.query.filter_by(program_id=program.id).first():
                    raise ValueError("Ce programme est utilisé par des dossiers. Modifiez les dossiers concernés avant de le supprimer.")
                db.session.delete(program); flash("Le programme a été supprimé.","success")
            elif action == "assign" and current_user.role=="admin":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                tutor_id=int(request.form.get("tutor_id")) if request.form.get("tutor_id") else None
                codir_id=int(request.form.get("codirector_id")) if request.form.get("codirector_id") else None
                if tutor_id and (not User.query.get(tutor_id) or User.query.get(tutor_id).role!="tutor"): raise ValueError("Le tuteur sélectionné doit avoir le rôle Tuteur.")
                if codir_id: raise ValueError("Seul un tuteur peut être affecté à un projet.")
                topic.tutor_id=tutor_id; topic.codirector_id=None
                db.session.add(WorkflowEvent(topic_id=topic.id,actor_id=current_user.id,action="Attribution de l'encadrement"))
                notify(tutor_id,topic.id,"Nouveau projet attribué",topic.title); notify(codir_id,topic.id,"Nouveau projet attribué",topic.title)
                flash("Encadrement mis à jour.","success")
            elif action == "decision":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                if not can_access(topic) or current_user.role=="student": abort(403)
                decision=request.form.get("decision")
                valid={"revision","approved","rejected","in_review"}
                if decision not in valid: raise ValueError("Décision non valide.")
                comment=request.form.get("comment","").strip()
                if decision in {"revision","rejected"} and len(comment)<8: raise ValueError("Veuillez motiver le retour ou le refus.")
                topic.status=decision
                db.session.add(WorkflowEvent(topic_id=topic.id,actor_id=current_user.id,action=decision,comment=comment))
                notify(topic.student_id,topic.id,"Mise à jour de votre dossier",comment or decision)
                flash("Décision enregistrée et historisée.","success")
            elif action == "message":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                if not can_access(topic): abort(403)
                body=request.form.get("body","").strip()
                if not body: raise ValueError("Le message ne peut pas être vide.")
                db.session.add(Message(topic_id=topic.id,sender_id=current_user.id,body=body))
                recipients={topic.student_id,topic.tutor_id,topic.codirector_id}-{None,current_user.id}
                for uid in recipients: notify(uid,topic.id,"Nouveau message sur votre projet",body[:180])
                flash("Message envoyé aux acteurs du projet.","success")
            elif action == "meeting":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                if not can_access(topic): abort(403)
                when=datetime.strptime(request.form.get("scheduled_at"),"%Y-%m-%dT%H:%M")
                db.session.add(Meeting(topic_id=topic.id,organizer_id=current_user.id,title=request.form.get("title","").strip(),scheduled_at=when,location=request.form.get("location","").strip(),notes=request.form.get("notes","").strip()))
                flash("Réunion planifiée.","success")
            elif action == "upload":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                if not can_access(topic): abort(403)
                file=request.files.get("document")
                if not file or not file.filename: raise ValueError("Sélectionnez un document.")
                ext=file.filename.rsplit(".",1)[-1].lower() if "." in file.filename else ""
                if ext not in ALLOWED: raise ValueError("Format non autorisé. Utilisez PDF, DOCX, DOC ou ODT.")
                safe=secure_filename(file.filename)
                folder=os.path.join(current_app.instance_path,"uploads",str(topic.id)); os.makedirs(folder,exist_ok=True)
                existing=DocumentVersion.query.filter_by(topic_id=topic.id,document_type=request.form.get("document_type","memoire")).count()
                stored=f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe}"
                file.save(os.path.join(folder,stored))
                db.session.add(DocumentVersion(topic_id=topic.id,uploader_id=current_user.id,filename=safe,storage_key=stored,version=existing+1,document_type=request.form.get("document_type","memoire"),comment=request.form.get("comment","").strip()))
                for uid in {topic.student_id,topic.tutor_id,topic.codirector_id}-{None,current_user.id}: notify(uid,topic.id,"Nouveau document déposé",safe)
                flash("Document déposé. Conservez également une copie locale.","success")
            elif action == "mark_read":
                note=Notification.query.filter_by(id=int(request.form.get("notification_id")),user_id=current_user.id).first_or_404()
                note.read_at=datetime.utcnow(); flash("Notification marquée comme lue.","success")
            else: raise ValueError("Action non reconnue ou non autorisée.")
            db.session.commit()
        except ValueError as exc:
            db.session.rollback(); flash(str(exc),"error")
        except Exception:
            db.session.rollback(); raise
        return redirect(url_for("modules.section",section=section))

    topics=visible_topics().all()
    users=User.query.order_by(User.full_name).all() if current_user.role=="admin" else []
    programs=AcademicProgram.query.filter_by(active=True).order_by(AcademicProgram.name).all()
    if section in {"etudiants","enseignants","utilisateurs"}:
        users=User.query.order_by(User.full_name).all()
        if section=="etudiants": users=[u for u in users if u.role=="student"]
        elif section=="enseignants": users=[u for u in users if u.role=="tutor"]
    topic_ids=[t.id for t in topics]
    messages=Message.query.filter(Message.topic_id.in_(topic_ids)).order_by(Message.created_at.desc()).limit(100).all() if topic_ids else []
    docs=DocumentVersion.query.filter(DocumentVersion.topic_id.in_(topic_ids)).order_by(DocumentVersion.created_at.desc()).all() if topic_ids else []
    meetings=Meeting.query.filter(Meeting.topic_id.in_(topic_ids)).order_by(Meeting.scheduled_at).all() if topic_ids else []
    history=WorkflowEvent.query.filter(WorkflowEvent.topic_id.in_(topic_ids)).order_by(WorkflowEvent.created_at.desc()).limit(100).all() if topic_ids else []
    notes=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    stats={"students":User.query.filter_by(role="student").count(),"tutors":User.query.filter_by(role="tutor").count(),"topics":ProjectTopic.query.count(),"pending":ProjectTopic.query.filter(ProjectTopic.status.in_(["draft","submitted","revision","in_review"])).count(),"approved":ProjectTopic.query.filter_by(status="approved").count()}
    return render_template("module.html",section=section,topics=topics,users=users,programs=programs,academic_sections=AcademicSection.query.filter_by(active=True).order_by(AcademicSection.name).all(),academic_sections_all=AcademicSection.query.order_by(AcademicSection.name).all(),messages=messages,docs=docs,meetings=meetings,history=history,notes=notes,stats=stats,roles=ROLES,now=datetime.utcnow())


@modules_bp.get("/api/etudiants/<string:matricule>")
@login_required
def student_by_matricule(matricule):
    if current_user.role not in {"admin","tutor"}:
        abort(403)
    student = User.query.filter_by(matricule=matricule.strip(), role="student").first_or_404()
    topic = ProjectTopic.query.filter_by(student_id=student.id).order_by(ProjectTopic.updated_at.desc()).first()
    return jsonify({"full_name":student.full_name,"matricule":student.matricule,"email":student.email,"mention":student.mention or student.mention_name or student.option_name or "","mention":student.mention or student.mention_name or student.option_name or "","promotion":student.promotion or "","subject":topic.title if topic else "Aucun sujet enregistré","program":topic.program.name if topic and topic.program else "","level":topic.program.level if topic and topic.program else "","tutor":topic.tutor.full_name if topic and topic.tutor else "À attribuer","codirector":topic.codirector.full_name if topic and topic.codirector else "À attribuer","status":topic.status if topic else "Sans sujet"})

@modules_bp.get("/rapports/imprimer")
@login_required
def print_student_report():
    if current_user.role != "admin": abort(403)
    query = User.query.filter_by(role="student")
    section_name = request.args.get("section", "").strip()
    mention = request.args.get("mention", "").strip()
    promotion = request.args.get("promotion", "").strip()
    if section_name: query = query.filter(User.section_name == section_name)
    if mention: query = query.filter(db.or_(User.mention == mention, User.mention_name == mention, User.option_name == mention))
    if promotion: query = query.filter(User.promotion == promotion)
    students = query.order_by(User.full_name.asc(), User.matricule.asc()).all()
    rows = [{"student":s,"topic":ProjectTopic.query.filter_by(student_id=s.id).order_by(ProjectTopic.updated_at.desc()).first()} for s in students]
    return render_template("print_students.html",rows=rows,now=datetime.utcnow(),institution=Institution.query.order_by(Institution.id.asc()).first(),filters={"section":section_name,"mention":mention,"promotion":promotion})

@modules_bp.get("/documents/<int:doc_id>")
@login_required
def download_document(doc_id):
    doc=DocumentVersion.query.get_or_404(doc_id)
    topic=ProjectTopic.query.get_or_404(doc.topic_id)
    if not can_access(topic): abort(403)
    folder=os.path.join(current_app.instance_path,"uploads",str(topic.id))
    return send_from_directory(folder,doc.storage_key,as_attachment=True,download_name=doc.filename)

@modules_bp.app_context_processor
def inject_unread_notifications():
    if current_user.is_authenticated:
        return {"unread_notifications":Notification.query.filter_by(user_id=current_user.id,read_at=None).count()}
    return {"unread_notifications":0}
