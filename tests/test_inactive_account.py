from tests.conftest import login


def test_inactive_account_cannot_authenticate(app, client):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="student@test.local").one()
        user.active = False
        db.session.commit()

    response = login(client, email="student@test.local")
    assert b"Adresse e-mail ou mot de passe incorrect" in response.data
    assert b"Bonjour Étudiante" not in response.data
