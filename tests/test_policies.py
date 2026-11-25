from types import SimpleNamespace

from app.policies import can_access_topic, can_create_topic_for, can_decide_topic


def user(user_id, role, active=True):
    return SimpleNamespace(id=user_id, role=role, active=active)


def topic(student_id=10, tutor_id=20, codirector_id=30):
    return SimpleNamespace(student_id=student_id, tutor_id=tutor_id, codirector_id=codirector_id)


def test_topic_access_is_limited_to_participants_and_management():
    record = topic()
    assert can_access_topic(user(10, "student"), record)
    assert can_access_topic(user(20, "tutor"), record)
    assert can_access_topic(user(30, "codirector"), record)
    assert can_access_topic(user(99, "admin"), record)
    assert not can_access_topic(user(99, "student"), record)
    assert not can_access_topic(None, record)


def test_only_management_roles_can_create_for_another_student():
    student = user(10, "student")
    assert can_create_topic_for(student, student)
    assert not can_create_topic_for(user(20, "tutor"), student)
    assert not can_create_topic_for(user(30, "codirector"), student)
    assert can_create_topic_for(user(99, "coordination"), student)
    assert not can_create_topic_for(user(99, "admin"), user(11, "tutor"))
    assert not can_create_topic_for(user(99, "admin"), user(11, "student", active=False))


def test_decision_rights_require_participation_or_management():
    record = topic()
    assert can_decide_topic(user(20, "tutor"), record)
    assert can_decide_topic(user(30, "codirector"), record)
    assert can_decide_topic(user(99, "department_head"), record)
    assert not can_decide_topic(user(10, "student"), record)
    assert not can_decide_topic(user(88, "tutor"), record)
