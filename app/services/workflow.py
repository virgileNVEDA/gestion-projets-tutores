"""Project workflow rules shared by HTTP controllers and tests."""

VALID_DECISIONS = frozenset({"revision", "approved", "rejected", "in_review"})
DECISIONS_REQUIRING_COMMENT = frozenset({"revision", "rejected"})


class WorkflowValidationError(ValueError):
    """Raised when a workflow transition is invalid."""


def apply_decision(topic, decision, comment=""):
    """Validate and apply a workflow decision to a project topic."""
    if decision not in VALID_DECISIONS:
        raise WorkflowValidationError("Décision non valide.")
    normalized_comment = (comment or "").strip()
    if decision in DECISIONS_REQUIRING_COMMENT and len(normalized_comment) < 8:
        raise WorkflowValidationError("Veuillez motiver le retour ou le refus.")
    topic.status = decision
    return normalized_comment
