from types import SimpleNamespace

import pytest

from app.services.workflow import WorkflowValidationError, apply_decision


@pytest.mark.parametrize("decision", ["revision", "rejected"])
def test_return_or_rejection_requires_a_reason(decision):
    topic = SimpleNamespace(status="submitted")
    with pytest.raises(WorkflowValidationError):
        apply_decision(topic, decision, "court")


def test_valid_approval_updates_status_without_mandatory_comment():
    topic = SimpleNamespace(status="submitted")
    assert apply_decision(topic, "approved", "") == ""
    assert topic.status == "approved"


def test_valid_revision_keeps_the_normalized_comment():
    topic = SimpleNamespace(status="submitted")
    assert apply_decision(topic, "revision", "  Merci de préciser la méthode  ") == "Merci de préciser la méthode"
    assert topic.status == "revision"


def test_unknown_decision_is_rejected():
    topic = SimpleNamespace(status="submitted")
    with pytest.raises(WorkflowValidationError):
        apply_decision(topic, "published", "commentaire valide")
