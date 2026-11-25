"""Validation helpers for project messages and supervision meetings."""
from datetime import datetime


class CommunicationValidationError(ValueError):
    """Raised when a message or meeting is incomplete."""


def validate_message(body):
    normalized = (body or "").strip()
    if not normalized:
        raise CommunicationValidationError("Le message ne peut pas être vide.")
    if len(normalized) > 10000:
        raise CommunicationValidationError("Le message dépasse la longueur maximale autorisée.")
    return normalized


def validate_meeting(title, scheduled_at, location="", notes=""):
    normalized_title = (title or "").strip()
    if len(normalized_title) < 3:
        raise CommunicationValidationError("Le titre de la réunion doit contenir au moins 3 caractères.")
    try:
        when = datetime.strptime(scheduled_at or "", "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        raise CommunicationValidationError("La date et l'heure de la réunion sont invalides.")
    return {
        "title": normalized_title,
        "scheduled_at": when,
        "location": (location or "").strip(),
        "notes": (notes or "").strip(),
    }
