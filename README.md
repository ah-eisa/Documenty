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

## Run In GitHub Codespaces

The repository includes `.devcontainer/devcontainer.json`, which installs Python dependencies, Tesseract, and Arabic OCR data, and forwards ports `8000` (FastAPI) and `8501` (Streamlit). Rebuild the container after changing the devcontainer configuration.

For an existing Codespace, start both services with:

```bash
./start.sh
```

Open the forwarded **Documenty Streamlit** port in the Ports panel. The backend health URL is the forwarded **Documenty API** port followed by `/health`. In this Codespace the URLs are:

- Streamlit: `https://solid-doodle-xrrqr66pg7g2vp69-8501.app.github.dev`
- FastAPI health: `https://solid-doodle-xrrqr66pg7g2vp69-8000.app.github.dev/health`

Codespace names are unique, so use the URLs shown in the Ports panel for another Codespace. When `CODESPACES=true`, Documenty derives the API public URL and Streamlit CORS origin from `CODESPACE_NAME` and `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN`. The Streamlit server calls FastAPI through `127.0.0.1`, while both processes bind to `0.0.0.0` only so forwarded ports can reach them. Production and non-Codespaces defaults remain local-only.

Configure Codespaces Secrets or environment variables before starting the app. Required secrets are `AUTH_PASSWORD_HASH`, `ENCRYPTION_KEY`, and `BACKUP_ENCRYPTION_KEY`; optional secrets are `OPENAI_API_KEY` and `TELEGRAM_BOT_TOKEN`. Never paste them into committed files or terminal commands.

Codespace persistence is not permanent backup storage. Source code is in GitHub; `data/app.db`, `files/`, `backups/`, and `logs/` live on the Codespace filesystem and can disappear when the Codespace is deleted or rebuilt. Create an encrypted backup from Settings or the API, then download it from `GET /api/settings/backups/{name}/download` and move it to a persistent external location. Keep the encryption key separately in Codespaces Secrets.

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
- `GET /api/settings/backups/{name}/download`
- `GET /health`

The scheduler synchronizes future document and event reminders at startup, checks due reminders hourly, and builds a daily report at 08:00 in `TIMEZONE`. The SQLite database is created at `data/app.db` on first backend startup.