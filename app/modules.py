import os
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from .extensions import db
from .models import User, AcademicProgram, ProjectTopic, WorkflowEvent, Message, DocumentVersion, Meeting, Notification, Institution, ROLES

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

def visible_topics():
    q = ProjectTopic.query
    if current_user.role == "student": q = q.filter_by(student_id=current_user.id)
    elif current_user.role == "tutor": q = q.filter_by(tutor_id=current_user.id)
    elif current_user.role == "codirector": q = q.filter_by(codirector_id=current_user.id)
    return q.order_by(ProjectTopic.updated_at.desc())

def can_access(topic):
    if current_user.role == "admin" or current_user.role in {"section_head","department_head","coordination"}: return True
    return current_user.id in {topic.student_id, topic.tutor_id, topic.codirector_id}

def notify(user_id, topic_id, title, body):
    if user_id and user_id != current_user.id:
        db.session.add(Notification(user_id=user_id, topic_id=topic_id, title=title, body=body))


@modules_bp.app_context_processor
def inject_institution():
    return {"institution": Institution.query.order_by(Institution.id.asc()).first()}

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
    if request.method == "POST":
        institution.name = request.form.get("institution_name", "").strip() or institution.name
        institution.acronym = request.form.get("acronym", "").strip() or None
        institution.logo_url = request.form.get("logo_url", "").strip() or None
        institution.primary_color = request.form.get("primary_color", "#142D49")
        institution.accent_color = request.form.get("accent_color", "#079B83")
        institution.progress_enabled = request.form.get("progress_enabled") == "on"
        institution.progress_color = request.form.get("progress_color", "#079B83")
        images = [line.strip() for line in request.form.get("carousel_images", "").splitlines() if line.strip()]
        if len(images) > 12:
            flash("Le carrousel accepte au maximum 12 images.", "error")
            return redirect(url_for("modules.settings"))
        if any(not (url.startswith("https://") or url.startswith("http://")) for url in images):
            flash("Chaque image doit avoir une adresse HTTPS ou HTTP valide.", "error")
            return redirect(url_for("modules.settings"))
        import json
        institution.carousel_images = json.dumps(images, ensure_ascii=False)
        db.session.commit()
        flash("Les paramètres de l’établissement ont été enregistrés.", "success")
        return redirect(url_for("modules.settings"))
    import json
    try:
        carousel_images = "\\n".join(json.loads(institution.carousel_images or "[]"))
    except (ValueError, TypeError):
        carousel_images = ""
    return render_template("settings.html", institution=institution, carousel_images=carousel_images)

@modules_bp.route("/<section>", methods=["GET","POST"])
@login_required
def section(section):
    allowed = {"etudiants","enseignants","programmes","sujets","encadrement","validations","messagerie","documents","reunions","rapports","notifications","utilisateurs"}
    if section not in allowed: abort(404)
    admin_sections = {"etudiants","enseignants","programmes","utilisateurs"}
    if section in admin_sections and current_user.role != "admin": abort(403)
    if section == "rapports" and current_user.role not in {"admin","section_head","department_head","coordination"}: abort(403)

    if request.method == "POST":
        action = request.form.get("action","")
        try:
            if action == "create_user" and current_user.role == "admin":
                email=request.form.get("email","").strip().lower()
                if User.query.filter_by(email=email).first(): raise ValueError("Cette adresse e-mail existe déjà.")
                role=request.form.get("role","student")
                if role not in ROLES: raise ValueError("Rôle invalide.")
                user=User(full_name=request.form.get("full_name","").strip(),email=email,role=role,option_name=request.form.get("option_name","").strip() or None,mention=request.form.get("mention","").strip() or None,promotion=request.form.get("promotion","").strip() or None)
                password=request.form.get("password","")
                if len(user.full_name)<3 or len(password)<10: raise ValueError("Nom obligatoire et mot de passe de 10 caractères minimum.")
                user.set_password(password); db.session.add(user); db.session.flush()
                if role == "student": user.matricule = f"PT{datetime.utcnow().year}-{user.id:06d}"
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
            elif action == "assign" and current_user.role=="admin":
                topic=ProjectTopic.query.get_or_404(int(request.form.get("topic_id")))
                tutor_id=int(request.form.get("tutor_id")) if request.form.get("tutor_id") else None
                codir_id=int(request.form.get("codirector_id")) if request.form.get("codirector_id") else None
                if tutor_id and User.query.get(tutor_id).role!="tutor": raise ValueError("Le directeur doit avoir le rôle Directeur de mémoire.")
                if codir_id and User.query.get(codir_id).role!="codirector": raise ValueError("Le codirecteur doit avoir le rôle Codirecteur.")
                topic.tutor_id=tutor_id; topic.codirector_id=codir_id
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
        elif section=="enseignants": users=[u for u in users if u.role in {"tutor","codirector","section_head","department_head"}]
    topic_ids=[t.id for t in topics]
    messages=Message.query.filter(Message.topic_id.in_(topic_ids)).order_by(Message.created_at.desc()).limit(100).all() if topic_ids else []
    docs=DocumentVersion.query.filter(DocumentVersion.topic_id.in_(topic_ids)).order_by(DocumentVersion.created_at.desc()).all() if topic_ids else []
    meetings=Meeting.query.filter(Meeting.topic_id.in_(topic_ids)).order_by(Meeting.scheduled_at).all() if topic_ids else []
    history=WorkflowEvent.query.filter(WorkflowEvent.topic_id.in_(topic_ids)).order_by(WorkflowEvent.created_at.desc()).limit(100).all() if topic_ids else []
    notes=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    stats={"students":User.query.filter_by(role="student").count(),"tutors":User.query.filter_by(role="tutor").count(),"topics":ProjectTopic.query.count(),"pending":ProjectTopic.query.filter(ProjectTopic.status.in_(["draft","submitted","revision","in_review"])).count(),"approved":ProjectTopic.query.filter_by(status="approved").count()}
    return render_template("module.html",section=section,topics=topics,users=users,programs=programs,messages=messages,docs=docs,meetings=meetings,history=history,notes=notes,stats=stats,roles=ROLES,now=datetime.utcnow())


@modules_bp.get("/api/etudiants/<string:matricule>")
@login_required
def student_by_matricule(matricule):
    if current_user.role not in {"admin","section_head","department_head","coordination","tutor","codirector"}:
        abort(403)
    student = User.query.filter_by(matricule=matricule.strip(), role="student").first_or_404()
    topic = ProjectTopic.query.filter_by(student_id=student.id).order_by(ProjectTopic.updated_at.desc()).first()
    return jsonify({"full_name":student.full_name,"matricule":student.matricule,"email":student.email,"option":student.option_name or "","mention":student.mention or "","promotion":student.promotion or "","subject":topic.title if topic else "Aucun sujet enregistré","program":topic.program.name if topic and topic.program else "","level":topic.program.level if topic and topic.program else "","tutor":topic.tutor.full_name if topic and topic.tutor else "À attribuer","codirector":topic.codirector.full_name if topic and topic.codirector else "À attribuer","status":topic.status if topic else "Sans sujet"})

@modules_bp.get("/rapports/imprimer")
@login_required
def print_student_report():
    if current_user.role not in {"admin","section_head","department_head","coordination"}: abort(403)
    students = User.query.filter_by(role="student").order_by(User.promotion.desc(),User.full_name.asc()).all()
    rows = [{"student":s,"topic":ProjectTopic.query.filter_by(student_id=s.id).order_by(ProjectTopic.updated_at.desc()).first()} for s in students]
    return render_template("print_students.html",rows=rows,now=datetime.utcnow())

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
