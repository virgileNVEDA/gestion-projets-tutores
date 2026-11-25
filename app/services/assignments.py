"""Validation des affectations d'encadrement académique."""


class AssignmentValidationError(ValueError):
    """Raised when an academic supervisor cannot be assigned."""


def validate_supervisor(user, expected_role, label):
    if user is None or user.role != expected_role or not user.active:
        raise AssignmentValidationError(
            f"{label} doit être un compte actif avec le rôle {label}."
        )
    return user
