from app.services.topics import TopicValidationError, validate_topic_data


def test_topic_data_is_trimmed_and_normalized():
    result = validate_topic_data("  Étude d'un système intégré  ", "  Contexte  ")
    assert result["title"] == "Étude d'un système intégré"
    assert result["problem_statement"] == "Contexte"


def test_topic_title_must_have_at_least_twelve_characters():
    try:
        validate_topic_data("Trop court")
    except TopicValidationError:
        return
    raise AssertionError("A validation error was expected")
