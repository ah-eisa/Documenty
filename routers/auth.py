from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from services import auth_service
from services.security import login_allowed

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_id = request.client.host if request.client else "unknown"
    if not login_allowed(client_id):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    token = auth_service.authenticate(db, payload.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from config import settings
    response.set_cookie("documenty_session", token, httponly=True, secure=settings.API_PUBLIC_URL.startswith("https://"), samesite="lax", max_age=settings.SESSION_TTL_HOURS * 3600)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    authorization = request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ").strip() or request.cookies.get("documenty_session")
    auth_service.revoke(db, token)
    response.delete_cookie("documenty_session")
    return {"success": True}


