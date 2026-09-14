"""FastAPI authentication dependencies and login throttling."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.db import get_db
from services import auth_service

_bearer = HTTPBearer(auto_error=False)
_attempts: dict[str, deque[float]] = defaultdict(deque)
_WINDOW_SECONDS = 300
_MAX_ATTEMPTS = 8


def login_allowed(client_id: str) -> bool:
    now = time.monotonic()
    attempts = _attempts[client_id]
    while attempts and now - attempts[0] > _WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _MAX_ATTEMPTS:
        return False
    attempts.append(now)
    return True


def current_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
):
    token = credentials.credentials if credentials else request.cookies.get("documenty_session")
    session = auth_service.get_session(db, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return session
