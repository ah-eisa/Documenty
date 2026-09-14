# Personal Operations Copilot

A local-first document and personal operations manager built with FastAPI, SQLite, and Streamlit. It accepts PDF, DOCX, XLSX, JPG, and PNG files, extracts metadata with local fallbacks or an OpenAI-compatible API, creates expiry reminders, and exposes a bilingual-friendly REST API plus a browser UI.

## Project layout

- `app.py`: FastAPI application and lifecycle scheduler
- `streamlit_app.py`: Streamlit frontend
- `database/`: SQLAlchemy models and repository operations
- `services/`: extraction, AI fallback, document processing, reminders, reports, and Telegram
- `routers/`: document, event, search, and settings endpoints
- `files/`, `data/`, and `logs/`: local runtime storage

## Requirements

- Python 3.11 or newer
- Tesseract OCR is optional, but required for image-only documents. Install Arabic language data when Arabic OCR is needed.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate with `.venv\\Scripts\\activate` and copy the environment file with `copy .env.example .env`.

The application works without an AI key by using heuristic extraction. Set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` in `.env` to enable structured extraction through an OpenAI-compatible endpoint. Telegram reminders are enabled when both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured.

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

The scheduler synchronizes future document and event reminders at startup, checks due reminders hourly, and builds a daily report at 08:00 in `TIMEZONE`.

## Validation

```bash
python -m compileall -q .
```

The SQLite database is created at `data/app.db` on first backend startup. Runtime files and logs are intentionally ignored by Git while their directories are retained with `.gitkeep` files.