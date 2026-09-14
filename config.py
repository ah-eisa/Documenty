from __future__ import annotations

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


class Settings:
    @property
    def APP_NAME(self) -> str: return os.getenv("APP_NAME", "Personal Operations Copilot")
    @property
    def HOST(self) -> str: return os.getenv("HOST") or ("0.0.0.0" if os.getenv("CODESPACES") == "true" else "127.0.0.1")
    @property
    def PORT(self) -> int: return int(os.getenv("PORT", "8000"))
    @property
    def API_BASE_URL(self) -> str: return os.getenv("API_BASE_URL", f"http://127.0.0.1:{self.PORT}")
    @property
    def API_PUBLIC_URL(self) -> str:
        configured = os.getenv("API_PUBLIC_URL", "").strip().rstrip("/")
        if configured:
            return configured
        if os.getenv("CODESPACES") == "true" and os.getenv("CODESPACE_NAME") and os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"):
            return f"https://{os.environ['CODESPACE_NAME']}-{self.PORT}.{os.environ['GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN']}"
        return self.API_BASE_URL
    @property
    def FRONTEND_ORIGINS(self) -> list[str]:
        raw = os.getenv("FRONTEND_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
        origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        if os.getenv("CODESPACES") == "true" and os.getenv("CODESPACE_NAME") and os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"):
            origins.append(f"https://{os.environ['CODESPACE_NAME']}-8501.{os.environ['GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN']}")
        return sorted(set(origins))
    @property
    def TIMEZONE(self) -> str: return os.getenv("TIMEZONE", "UTC")
    @property
    def LOG_LEVEL(self) -> str: return os.getenv("LOG_LEVEL", "INFO").upper()
    @property
    def DATABASE_URL(self) -> str: return os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}")
    @property
    def FILES_DIR(self) -> Path: return _resolve_path(os.getenv("FILES_DIR"), BASE_DIR / "files")
    @property
    def LOGS_DIR(self) -> Path: return _resolve_path(os.getenv("LOGS_DIR"), BASE_DIR / "logs")
    @property
    def OPENAI_API_KEY(self) -> str: return os.getenv("OPENAI_API_KEY", "")
    @property
    def OPENAI_BASE_URL(self) -> str: return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    @property
    def OPENAI_MODEL(self) -> str: return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str: return os.getenv("TELEGRAM_BOT_TOKEN", "")
    @property
    def TELEGRAM_CHAT_ID(self) -> str: return os.getenv("TELEGRAM_CHAT_ID", "")
    @property
    def REMINDER_DAYS_DEFAULT(self) -> list[int]:
        return sorted({int(x.strip()) for x in os.getenv("REMINDER_DAYS_DEFAULT", "90,30,7,3,1").split(",") if x.strip().isdigit()}, reverse=True)
    @property
    def OCR_LANGUAGE(self) -> str: return os.getenv("OCR_LANGUAGE", "eng")
    @property
    def TESSERACT_CMD(self) -> str: return os.getenv("TESSERACT_CMD", "")
    @property
    def MAX_AI_TEXT_CHARS(self) -> int: return int(os.getenv("MAX_AI_TEXT_CHARS", "12000"))
    @property
    def MAX_UPLOAD_SIZE_MB(self) -> int: return max(1, int(os.getenv("MAX_UPLOAD_SIZE_MB", "25")))
    @property
    def AUTH_PASSWORD_HASH(self) -> str: return os.getenv("AUTH_PASSWORD_HASH", "")
    @property
    def SESSION_TTL_HOURS(self) -> int: return max(1, int(os.getenv("SESSION_TTL_HOURS", "12")))
    @property
    def ENCRYPTION_KEY(self) -> str: return os.getenv("ENCRYPTION_KEY", "")
    @property
    def BACKUP_ENCRYPTION_KEY(self) -> str: return os.getenv("BACKUP_ENCRYPTION_KEY", "") or self.ENCRYPTION_KEY
    @property
    def BACKUP_DIR(self) -> Path: return _resolve_path(os.getenv("BACKUP_DIR"), BASE_DIR / "backups")
    @property
    def BACKUP_RETENTION(self) -> int: return max(1, int(os.getenv("BACKUP_RETENTION", "7")))


settings = Settings()


def ensure_dirs() -> None:
    settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def update_env_file(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pending = dict(updates)
    result = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in pending:
            result.append(f"{key}={pending.pop(key)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in pending.items())
    ENV_PATH.write_text("\n".join(result) + "\n", encoding="utf-8")
    os.environ.update({key: str(value) for key, value in updates.items()})
