"""Safe local document storage.

The storage root is configurable so a persistent volume or object-storage adapter
can be introduced without changing the academic routes. The default remains the
application instance directory for backward compatibility.
"""
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = frozenset({"pdf", "doc", "docx", "odt", "xlsx", "pptx", "png", "jpg", "jpeg"})
ALLOWED_DOCUMENT_TYPES = frozenset({"memoire", "proposition", "chapitre", "annexe", "autre"})


class DocumentValidationError(ValueError):
    """Raised when an uploaded document is invalid."""


def validate_document(file, max_bytes, document_type="memoire"):
    if file is None or not getattr(file, "filename", ""):
        raise DocumentValidationError("Sélectionnez un document.")
    original = file.filename
    if "." not in original:
        raise DocumentValidationError("Le fichier doit avoir une extension autorisée.")
    extension = original.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError("Format non autorisé. Utilisez PDF, DOCX, DOC, ODT, XLSX, PPTX, PNG ou JPG.")
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise DocumentValidationError("Type de document non reconnu.")
    filename = secure_filename(original)
    if not filename:
        raise DocumentValidationError("Nom de fichier invalide.")
    stream = file.stream
    current = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current)
    if size <= 0:
        raise DocumentValidationError("Le fichier est vide.")
    if size > max_bytes:
        raise DocumentValidationError("Le document dépasse la taille maximale autorisée.")
    return filename, extension, size


class LocalDocumentStorage:
    """Local storage implementation; point STORAGE_ROOT at a persistent volume."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def save(self, topic_id, file, filename):
        folder = (self.root / str(int(topic_id))).resolve()
        if self.root not in folder.parents:
            raise DocumentValidationError("Chemin de stockage invalide.")
        folder.mkdir(parents=True, exist_ok=True)
        storage_key = f"{uuid4().hex}_{filename}"
        destination = folder / storage_key
        file.save(destination)
        return storage_key

    def path_for(self, topic_id):
        folder = (self.root / str(int(topic_id))).resolve()
        if self.root not in folder.parents:
            raise DocumentValidationError("Chemin de stockage invalide.")
        return folder
