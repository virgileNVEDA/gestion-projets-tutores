import pytest

from app import create_app
from app.extensions import db
from app.models import Institution, User


@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-only-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
    })
    with app.app_context():
        db.create_all()
        db.session.add(Institution(name="Établissement de test", acronym="TEST"))
        admin = User(full_name="Administrateur Test", email="admin@test.local", role="admin")
        admin.set_password("MotDePasse-Test-2026!")
        student = User(full_name="Étudiante Test", email="student@test.local", role="student")
        student.set_password("MotDePasse-Test-2026!")
        tutor = User(full_name="Directeur Test", email="tutor@test.local", role="tutor")
        tutor.set_password("MotDePasse-Test-2026!")
        db.session.add_all([admin, student, tutor])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="admin@test.local", password="MotDePasse-Test-2026!"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
