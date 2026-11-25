"""Centralized authorization rules for academic records.

Keep these functions independent from Flask globals so they can be tested directly.
"""

MANAGEMENT_ROLES = frozenset({"admin", "section_head", "department_head", "coordination"})
STAFF_ROLES = frozenset({"admin", "section_head", "department_head", "coordination", "tutor", "codirector"})


def can_access_topic(user, topic):
    if user is None or topic is None:
        return False
    if user.role in MANAGEMENT_ROLES:
        return True
    return user.id in {topic.student_id, topic.tutor_id, topic.codirector_id}


def can_create_topic_for(user, student):
    if user is None or student is None or student.role != "student" or not student.active:
        return False
    if user.role == "student":
        return user.id == student.id
    return user.role in MANAGEMENT_ROLES


def can_decide_topic(user, topic):
    if not can_access_topic(user, topic):
        return False
    return user.role in MANAGEMENT_ROLES or (
        user.role == "tutor" and topic.tutor_id == user.id
    ) or (
        user.role == "codirector" and topic.codirector_id == user.id
    )
