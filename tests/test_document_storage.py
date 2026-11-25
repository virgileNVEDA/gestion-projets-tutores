from io import BytesIO

from werkzeug.datastructures import FileStorage

from app.services.documents import LocalDocumentStorage


def test_local_storage_saves_inside_topic_folder(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    upload = FileStorage(stream=BytesIO(b"contenu"), filename="rapport.pdf")
    key = storage.save(42, upload, "rapport.pdf")
    saved = storage.path_for(42) / key
    assert saved.is_file()
    assert saved.read_bytes() == b"contenu"
    assert key.endswith("_rapport.pdf")
