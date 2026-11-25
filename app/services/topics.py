"""Validation métier des dossiers de projets tutorés."""


class TopicValidationError(ValueError):
    """Raised when project topic data is incomplete or invalid."""


def validate_topic_data(title, problem_statement="", objectives="", methodology="", keywords=""):
    normalized = {
        "title": (title or "").strip(),
        "problem_statement": (problem_statement or "").strip(),
        "objectives": (objectives or "").strip(),
        "methodology": (methodology or "").strip(),
        "keywords": (keywords or "").strip(),
    }
    if len(normalized["title"]) < 12:
        raise TopicValidationError("Le titre doit contenir au moins 12 caractères.")
    return normalized
