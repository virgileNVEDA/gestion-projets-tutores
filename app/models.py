from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import db, login_manager

ROLES = {
    "admin": "Administration",
    "student": "Étudiant",
    "tutor": "Tuteur",
    "codirector": "Codirecteur",
    "section_head": "Chef de section",
    "department_head": "Chef de département",
    "coordination": "Coordination académique",
}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(140), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="student")
    matricule = db.Column(db.String(60), unique=True, nullable=True, index=True)
    option_name = db.Column(db.String(120))
    mention = db.Column(db.String(120))
    promotion = db.Column(db.String(80))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    profile_photo_data = db.Column(db.Text, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_online(self):
        return bool(self.last_seen_at and (datetime.utcnow() - self.last_seen_at).total_seconds() <= 180)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self):
        return ROLES.get(self.role, self.role)


class AcademicProgram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    level = db.Column(db.String(80), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)


class ProjectTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    problem_statement = db.Column(db.Text)
    objectives = db.Column(db.Text)
    methodology = db.Column(db.Text)
    keywords = db.Column(db.String(500))
    status = db.Column(db.String(40), default="draft", nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    codirector_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    program_id = db.Column(db.Integer, db.ForeignKey("academic_program.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[student_id], backref="student_topics")
    tutor = db.relationship("User", foreign_keys=[tutor_id], backref="tutored_topics")
    codirector = db.relationship("User", foreign_keys=[codirector_id], backref="codirected_topics")
    program = db.relationship("AcademicProgram", backref="topics")


class WorkflowEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("project_topic.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    topic = db.relationship("ProjectTopic", backref="history")
    actor = db.relationship("User")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("project_topic.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    topic = db.relationship("ProjectTopic", backref="messages")
    sender = db.relationship("User")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class DocumentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("project_topic.id"), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    document_type = db.Column(db.String(40), nullable=False, default="memoire")
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    topic = db.relationship("ProjectTopic", backref="document_versions")
    uploader = db.relationship("User")


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("project_topic.id"), nullable=False, index=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(180))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    topic = db.relationship("ProjectTopic", backref="meetings")
    organizer = db.relationship("User")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("project_topic.id"))
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User", backref="notifications")
    topic = db.relationship("ProjectTopic")


class Institution(db.Model):
    """Identité et préférences visuelles d'un établissement."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, default="Établissement académique")
    acronym = db.Column(db.String(40), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    logo_data = db.Column(db.Text, nullable=True)
    secondary_logo_data = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(80), nullable=True)
    contact_email = db.Column(db.String(180), nullable=True)
    website = db.Column(db.String(240), nullable=True)
    motto = db.Column(db.String(240), nullable=True)
    academic_year = db.Column(db.String(40), nullable=True)
    progress_image_data = db.Column(db.Text, nullable=True)
    primary_color = db.Column(db.String(20), nullable=False, default="#142D49")
    accent_color = db.Column(db.String(20), nullable=False, default="#079B83")
    carousel_images = db.Column(db.Text, nullable=True)
    progress_enabled = db.Column(db.Boolean, nullable=False, default=True)
    progress_color = db.Column(db.String(20), nullable=False, default="#079B83")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
