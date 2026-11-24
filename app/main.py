from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from .models import ProjectTopic, User

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    from flask import redirect, url_for
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


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
                           status_chart=status_chart, monthly_chart=monthly_chart)
