from flask import Blueprint, render_template
from flask_login import login_required, current_user
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
    return render_template("dashboard.html", topics=topics, stats=stats)
