import pytest

from app.services.communications import (
    CommunicationValidationError,
    validate_meeting,
    validate_message,
)


def test_message_is_trimmed():
    assert validate_message("  Bonjour  ") == "Bonjour"


def test_empty_message_is_rejected():
    with pytest.raises(CommunicationValidationError):
        validate_message("  ")


def test_meeting_fields_are_normalized():
    meeting = validate_meeting("  Suivi du mémoire ", "2026-12-01T10:30", " Salle 2 ", " Notes ")
    assert meeting["title"] == "Suivi du mémoire"
    assert meeting["location"] == "Salle 2"
    assert meeting["notes"] == "Notes"
    assert meeting["scheduled_at"].hour == 10


def test_invalid_meeting_date_is_rejected():
    with pytest.raises(CommunicationValidationError):
        validate_meeting("Réunion", "date impossible")
