import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.auth_service import hash_password

ROOT = Path('/tmp/documenty-pytest')
ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('AUTH_PASSWORD_HASH', hash_password('Documenty-test-password-2026'))
os.environ.setdefault('DATABASE_URL', f'sqlite:///{ROOT / "test.db"}')
os.environ.setdefault('FILES_DIR', str(ROOT / 'files'))
os.environ.setdefault('LOGS_DIR', str(ROOT / 'logs'))
os.environ.setdefault('BACKUP_DIR', str(ROOT / 'backups'))
os.environ.setdefault('BACKUP_ENCRYPTION_KEY', '8i6V4m7cGJ0tYQk4q2oPjO9Yd3J7pQ5xA3bK1sN6cR8=')
os.environ.setdefault('ENCRYPTION_KEY', '8i6V4m7cGJ0tYQk4q2oPjO9Yd3J7pQ5xA3bK1sN6cR8=')

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post('/api/auth/login', json={'password': 'Documenty-test-password-2026'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}
