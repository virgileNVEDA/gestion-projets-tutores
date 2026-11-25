from tests.conftest import login


def test_tutor_cannot_create_a_topic_for_a_student(client):
    login(client, email="tutor@test.local")
    response = client.post(
        "/modules/sujets",
        data={
            "action": "create_topic",
            "student_id": "2",
            "title": "Sujet de test suffisamment long",
            "problem_statement": "Problématique de test",
        },
    )
    assert response.status_code == 403


def test_student_cannot_open_administration_modules(client):
    login(client, email="student@test.local")
    response = client.get("/modules/etudiants")
    assert response.status_code == 403
