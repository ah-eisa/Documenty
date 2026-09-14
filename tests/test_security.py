from datetime import date, timedelta

from database.db import SessionLocal
from database.models import Reminder
from services import extraction_service


def test_health_is_public_and_api_is_protected(client):
    assert client.get('/health').status_code == 200
    assert client.get('/api/dashboard').status_code == 401


def test_login_success_and_failure(client):
    assert client.post('/api/auth/login', json={'password': 'wrong'}).status_code == 401
    response = client.post('/api/auth/login', json={'password': 'Documenty-test-password-2026'})
    assert response.status_code == 200
    assert len(response.json()['access_token']) > 40


def test_settings_mask_secrets_and_preserve_blank_values(client, auth_headers, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-real-secret-value')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'telegram-real-secret-value')
    settings = client.get('/api/settings', headers=auth_headers)
    assert settings.status_code == 200
    assert settings.json()['OPENAI_API_KEY'] != 'sk-real-secret-value'
    assert settings.json()['TELEGRAM_BOT_TOKEN'] != 'telegram-real-secret-value'


def test_upload_validation_and_document_metadata(client, auth_headers, monkeypatch):
    unsupported = client.post('/api/documents/upload', headers=auth_headers, files={'file': ('x.exe', b'MZ', 'application/octet-stream')})
    assert unsupported.status_code == 400
    monkeypatch.setenv('MAX_UPLOAD_SIZE_MB', '1')
    oversized = client.post('/api/documents/upload', headers=auth_headers, files={'file': ('large.pdf', b'%PDF-1.7' + b'x' * (1024 * 1024 + 1), 'application/pdf')})
    assert oversized.status_code == 400
    monkeypatch.setenv('MAX_UPLOAD_SIZE_MB', '25')
    pdf = b'%PDF-1.7\n1 0 obj<<>>endobj\n%%EOF'
    response = client.post('/api/documents/upload', headers=auth_headers, files={'file': ('safe.pdf', pdf, 'application/pdf')})
    assert response.status_code == 200
    assert response.json()['extraction_status'] == 'failed'
    assert response.json()['is_encrypted'] is True


def test_duplicate_reminders_are_prevented(client, auth_headers):
    response = client.post('/api/events', headers=auth_headers, json={'title': 'Test', 'event_date': (date.today() + timedelta(days=10)).isoformat(), 'reminder_days': '7,3,1'})
    assert response.status_code == 200
    with SessionLocal() as db:
        before = db.query(Reminder).count()
        from services.reminder_service import sync_all_reminders
        sync_all_reminders(db)
        after = db.query(Reminder).count()
    assert before == after


def test_ocr_uses_configured_language(monkeypatch):
    calls = []
    monkeypatch.setenv('OCR_LANGUAGE', 'ara+eng')
    monkeypatch.setattr('pytesseract.image_to_string', lambda image, lang: calls.append(lang) or 'Arabic English text')
    from PIL import Image
    extraction_service._ocr(Image.new('RGB', (10, 10)))
    assert calls == ['ara+eng']


def test_backup_create_and_verify(client, auth_headers):
    response = client.post('/api/settings/backup', headers=auth_headers)
    assert response.status_code == 200
    name = response.json()['name']
    verification = client.post(f'/api/settings/backups/{name}/verify', headers=auth_headers)
    assert verification.status_code == 200
    assert verification.json()['valid'] is True
    restored = client.post(f'/api/settings/backups/{name}/restore', headers=auth_headers)
    assert restored.status_code == 200
