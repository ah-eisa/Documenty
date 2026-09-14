# Personal Operations Copilot

A local-first document and personal operations manager built with FastAPI, SQLite, and Streamlit. It accepts PDF, DOCX, XLSX, JPG, and PNG files, extracts metadata with local fallbacks or an OpenAI-compatible API, creates expiry reminders, and exposes a bilingual-friendly REST API plus a browser UI.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate with `.venv\\Scripts\\activate` and copy the environment file with `copy .env.example .env`.

## Documenty Personal Document Vault

Documenty is a local-first personal document vault built with FastAPI, SQLite, local storage, Streamlit, Tesseract OCR, an OpenAI-compatible extraction service, Telegram reminders, and APScheduler.

### Authentication

The API and Streamlit UI require the configured single-user password. Store only a PBKDF2 hash in `.env`:

```bash
python -m services.auth_service
```

Copy the generated value into `AUTH_PASSWORD_HASH`. The password is never stored or returned. Login sessions are opaque bearer tokens; only their hashes are stored in SQLite. Login attempts are rate-limited in memory. Set `SESSION_TTL_HOURS` to control expiry.

Generate encryption keys with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set `ENCRYPTION_KEY` to encrypt uploaded files at rest and `BACKUP_ENCRYPTION_KEY` to encrypt backups. Never commit `.env` or these keys.

## Security model

- `/health` and login are public; application APIs require authentication.
- CORS defaults to the local Streamlit origins in `FRONTEND_ORIGINS`.
- The backend binds to `127.0.0.1` by default.
- Uploads validate extension, MIME/signature, size, and PDF structure.
- Files receive UUID-based internal names and are never executed.
- Existing unencrypted files remain readable; new files are encrypted when configured.
- Settings responses mask OpenAI and Telegram secrets, and blank secret updates leave existing values unchanged.
- Unexpected server errors return a generic message and secrets are excluded from logs.

## OCR and extraction

Install Tesseract separately for image or scanned-PDF OCR. Set `OCR_LANGUAGE=ara+eng` for Arabic and English. `TESSERACT_CMD` may point to a Windows executable. Text extraction records `success` or `failed`, the source, and a bounded error message. PDF extraction tries embedded text, PyMuPDF, and OCR. The app remains usable without an AI key and uses deterministic heuristics instead.

AI output is parsed as JSON and only valid, usable fields can replace heuristic values. Configure `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_API_KEY` for any compatible Chat Completions provider.

## Backups

Backups are encrypted archives containing the SQLite database, uploaded files, and non-secret configuration metadata. Configure `BACKUP_DIR`, `BACKUP_RETENTION`, and `BACKUP_ENCRYPTION_KEY`. The settings API supports create, list, verify, and restore operations. The service uses a local file interface so a future Google Drive provider can be added without changing backup contents or validation.

Do not restore while the backend is writing to the database. Restart the backend after restoring. Backups currently support SQLite only.

## Features

- Authenticated dashboard with 7, 30, and 90-day expiry counts
- PDF, DOCX, XLSX, JPG, JPEG, and PNG uploads
- Metadata extraction, full-text search across extracted text, and structured expiry filters
- Document view, metadata editing, download, deletion, and manual reprocessing
- Events, idempotent reminders, overdue handling, Telegram alerts, and daily reports
- Encrypted local backups with retention and integrity verification

## Tests and validation

```bash
.venv/bin/python -m compileall -q app.py config.py schemas.py database services routers scheduler streamlit_app.py
.venv/bin/pytest -q
```

Runtime directories and `.env` are ignored by Git. Existing SQLite databases receive new columns through additive startup migration logic; no destructive schema changes are performed.

## Production notes

Keep the service behind a private network or reverse proxy, use HTTPS before allowing non-local access, provide secrets through a secret manager, use a persistent encrypted storage volume, and disable `--reload`. Add a remote backup provider only after validating key management and restore procedures.

## Run

Start the backend in one terminal:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in another terminal:

```bash
streamlit run streamlit_app.py
```

The API is available at `http://127.0.0.1:8000`, Swagger at `/docs`, and Streamlit normally at `http://localhost:8501`.

## API highlights

- `POST /api/documents/upload`
- `GET|PUT|DELETE /api/documents`
- `GET|POST|PUT|DELETE /api/events`
- `GET /api/search?q=...`
- `GET /api/dashboard`
- `GET|PUT /api/settings`
- `GET /health`

The scheduler synchronizes future document and event reminders at startup, checks due reminders hourly, and builds a daily report at 08:00 in `TIMEZONE`. The SQLite database is created at `data/app.db` on first backend startup.