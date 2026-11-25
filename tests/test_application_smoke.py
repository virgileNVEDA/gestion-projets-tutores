from tests.conftest import login


def test_public_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"PROJETS" in response.data or b"projet" in response.data.lower()


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")
    assert response.status_code in (302, 401)
    assert "/auth/login" in response.location


def test_admin_can_login_and_open_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"dashboard-v3" in response.data
    assert "Bonjour Administrateur".encode("utf-8") in response.data
    assert b"Projets r" in response.data


def test_student_can_login_and_open_dashboard(client):
    response = login(client, email="student@test.local")
    assert response.status_code == 200
    assert b"dashboard-v3" in response.data
    assert "Bonjour Étudiante".encode("utf-8") in response.data
