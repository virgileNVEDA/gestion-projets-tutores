from io import BytesIO
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import FileStorage

from app.services.documents import DocumentValidationError, validate_document


def upload(name, data=b"document"):
    return FileStorage(stream=BytesIO(data), filename=name)


def test_document_validation_returns_safe_filename_and_size():
    name, extension, size = validate_document(upload("rapport final.pdf"), 1024)
    assert name == "rapport_final.pdf"
    assert extension == "pdf"
    assert size == 8


@pytest.mark.parametrize("name", ["script.exe", "sans_extension"])
def test_document_validation_rejects_unsupported_extensions(name):
    with pytest.raises(DocumentValidationError):
        validate_document(upload(name), 1024)


def test_document_validation_rejects_empty_or_oversized_files():
    with pytest.raises(DocumentValidationError):
        validate_document(upload("vide.pdf", b""), 1024)
    with pytest.raises(DocumentValidationError):
        validate_document(upload("grand.pdf", b"12345"), 4)


def test_document_validation_rejects_unknown_document_type():
    with pytest.raises(DocumentValidationError):
        validate_document(upload("rapport.pdf"), 1024, "unknown")
