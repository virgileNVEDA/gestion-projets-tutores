from types import SimpleNamespace

import pytest

from app.services.assignments import AssignmentValidationError, validate_supervisor


@pytest.mark.parametrize("user", [None, SimpleNamespace(role="student", active=True), SimpleNamespace(role="tutor", active=False)])
def test_invalid_supervisor_is_rejected(user):
    with pytest.raises(AssignmentValidationError):
        validate_supervisor(user, "tutor", "Directeur de mémoire")


def test_active_supervisor_with_expected_role_is_accepted():
    user = SimpleNamespace(role="tutor", active=True)
    assert validate_supervisor(user, "tutor", "Directeur de mémoire") is user
