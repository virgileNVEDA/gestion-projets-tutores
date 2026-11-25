from datetime import datetime
import re
import unicodedata
from difflib import SequenceMatcher
from flask import Blueprint, render_template, request, abort, make_response
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from .models import ProjectTopic, User

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    from flask import redirect, url_for
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("public_home.html")



def _normalize_matricule(value):
    """Normalise un matricule pour ignorer accents, espaces et ponctuation."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


@main_bp.get("/recherche-etudiant")
def public_student_lookup():
    matricule = request.args.get("matricule", "").strip()
    student = None
    search_match_note = None
    if matricule:
        # D'abord la recherche exacte, puis la comparaison tolérante aux petites fautes.
        student = User.query.filter_by(matricule=matricule, role="student", active=True).first()
        if not student:
            wanted = _normalize_matricule(matricule)
            if len(wanted) >= 5:
                candidates = User.query.filter(
                    User.role == "student", User.active.is_(True), User.matricule.isnot(None)
                ).all()
                ranked = []
                for candidate in candidates:
                    normalized = _normalize_matricule(candidate.matricule)
                    if normalized:
                        ranked.append((SequenceMatcher(None, wanted, normalized).ratio(), candidate))
                ranked.sort(key=lambda item: item[0], reverse=True)
                if ranked and ranked[0][0] >= 0.86:
                    # En cas de deux matricules proches, ne jamais choisir arbitrairement.
                    second_score = ranked[1][0] if len(ranked) > 1 else 0
                    if ranked[0][0] - second_score >= 0.07:
                        student = ranked[0][1]
                        search_match_note = (
                            "Nous avons corrigé une petite erreur de saisie et trouvé le matricule "
                            + student.matricule + ". Vérifiez qu’il s’agit bien du vôtre."
                        )
    topic = ProjectTopic.query.filter_by(student_id=student.id).order_by(ProjectTopic.updated_at.desc()).first() if student else None
    return render_template(
        "public_home.html", student=student, topic=topic, matricule=matricule,
        searched=bool(matricule), search_match_note=search_match_note
    )

@main_bp.get("/fiche-etudiant/<string:matricule>/imprimer")
def public_student_print(matricule):
    student = User.query.filter_by(matricule=matricule, role="student", active=True).first_or_404()
    topic = ProjectTopic.query.filter_by(student_id=student.id).order_by(ProjectTopic.updated_at.desc()).first()
    return render_template("public_student_print.html", student=student, topic=topic, now=datetime.utcnow())

@main_bp.get("/export-etudiants.csv")
@login_required
def export_students_csv():
    if current_user.role not in {"admin","section_head","department_head","coordination"}: abort(403)
    import csv, io
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Matricule","Nom complet","Option","Mention","Promotion","Sujet","Programme","Niveau","Tuteur","Codirecteur","Statut"])
    students = User.query.filter_by(role="student").order_by(User.full_name.asc()).all()
    for student in students:
        topic = ProjectTopic.query.filter_by(student_id=student.id).order_by(ProjectTopic.updated_at.desc()).first()
        writer.writerow([student.matricule or "",student.full_name,student.option_name or "",student.mention or "",student.promotion or "",topic.title if topic else "",topic.program.name if topic and topic.program else "",topic.program.level if topic and topic.program else "",topic.tutor.full_name if topic and topic.tutor else "",topic.codirector.full_name if topic and topic.codirector else "",topic.status if topic else ""])
    response = make_response("\\ufeff" + buffer.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=liste_academique_etudiants.csv"
    return response

@main_bp.get("/dashboard")
@login_required
def dashboard():
    role = current_user.role
    query = ProjectTopic.query
    if role == "student":
        query = query.filter_by(student_id=current_user.id)
    elif role == "tutor":
        query = query.filter_by(tutor_id=current_user.id)
    elif role == "codirector":
        query = query.filter_by(codirector_id=current_user.id)
    topics = query.order_by(ProjectTopic.updated_at.desc()).limit(8).all()

    if role == "admin":
        stats = {
            "students": User.query.filter_by(role="student").count(),
            "tutors": User.query.filter_by(role="tutor").count(),
            "topics": ProjectTopic.query.count(),
            "pending": ProjectTopic.query.filter(ProjectTopic.status.in_(["draft", "submitted", "revision"])).count(),
        }
    else:
        stats = {"students": None, "tutors": None, "topics": query.count(),
                 "pending": query.filter(ProjectTopic.status.in_(["draft", "submitted", "revision"])).count()}

    # Graphiques calculés à partir des dossiers réellement accessibles à l'utilisateur.
    status_rows = query.with_entities(ProjectTopic.status, func.count(ProjectTopic.id)).group_by(ProjectTopic.status).all()
    labels = {
        "draft": "Brouillon", "submitted": "Soumis", "revision": "À corriger",
        "approved": "Validé", "rejected": "Refusé", "in_review": "En examen"
    }
    palette = {
        "draft": "#8b9bad", "submitted": "#3986d7", "revision": "#e5a52b",
        "approved": "#079b83", "rejected": "#d65b63", "in_review": "#8066c7"
    }
    status_chart = [{"key": key, "label": labels.get(key, key.replace("_", " ").title()),
                     "count": count, "color": palette.get(key, "#5d8fb5")}
                    for key, count in status_rows]
    total_chart = sum(item["count"] for item in status_chart) or 1
    for item in status_chart:
        item["percent"] = round(item["count"] * 100 / total_chart)

    now = datetime.utcnow()
    month_names = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    monthly_chart = []
    for offset in range(5, -1, -1):
        month = now.month - offset
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        count = query.filter(
            extract("year", ProjectTopic.created_at) == year,
            extract("month", ProjectTopic.created_at) == month
        ).count()
        monthly_chart.append({"label": month_names[month - 1], "count": count})
    max_month = max([item["count"] for item in monthly_chart] or [0]) or 1
    for item in monthly_chart:
        item["height"] = max(8, round(item["count"] * 100 / max_month)) if item["count"] else 3

    return render_template("dashboard.html", topics=topics, stats=stats,
                           status_chart=status_chart, monthly_chart=monthly_chart,
                           now=now)
