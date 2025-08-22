import os
import sys
import tempfile
from fastapi.testclient import TestClient

# Ensure the src directory is on the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set credentials and output directory before importing the app
os.environ['DOCROUTER_USER'] = 'user'
os.environ['DOCROUTER_PASS'] = 'pass'
os.environ['OUTPUT_DIR'] = tempfile.mkdtemp()

from web_app import server  # noqa: E402


def _mock_generate_metadata(text: str):
    return {
        'category': None,
        'subcategory': None,
        'issuer': None,
        'person': None,
        'doc_type': None,
        'date': '2024-01-01',
        'amount': None,
        'tags': [],
        'suggested_filename': None,
        'description': None,
    }


def test_upload_retrieve_and_download(monkeypatch):
    monkeypatch.setattr(server.metadata_generation, 'generate_metadata', _mock_generate_metadata)
    server.METADATA_STORE.clear()
    client = TestClient(server.app)

    response = client.post('/upload', files={'file': ('example.txt', b'content')}, auth=('user', 'pass'))
    assert response.status_code == 200
    data = response.json()
    file_id = data['id']

    meta = client.get(f'/metadata/{file_id}', auth=('user', 'pass'))
    assert meta.status_code == 200
    assert meta.json() == data['metadata']

    files_resp = client.get('/files', auth=('user', 'pass'))
    assert files_resp.status_code == 200
    assert any(f['id'] == file_id for f in files_resp.json())

    download_resp = client.get(f'/download/{file_id}', auth=('user', 'pass'))
    assert download_resp.status_code == 200
    assert download_resp.content == b'content'


def test_invalid_credentials():
    client = TestClient(server.app)

    resp = client.post('/upload', files={'file': ('example.txt', b'content')}, auth=('user', 'wrong'))
    assert resp.status_code == 401

    resp2 = client.get('/files', auth=('user', 'wrong'))
    assert resp2.status_code == 401

