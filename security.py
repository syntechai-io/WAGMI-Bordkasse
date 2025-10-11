from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv
import secrets

load_dotenv()

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))

serializer = URLSafeTimedSerializer(SESSION_SECRET)

def create_session_token(username: str) -> str:
    return serializer.dumps({"username": username})

def verify_session_token(token: str):
    try:
        return serializer.loads(token, max_age=86400)
    except:
        return None

def get_current_user(request: Request):
    token = request.session.get("user_token")
    if not token:
        return None
    user_data = verify_session_token(token)
    return user_data.get("username") if user_data else None

def require_admin(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def verify_csrf_token(request: Request, token: str) -> bool:
    session_token = request.session.get("csrf_token")
    return bool(session_token and session_token == token)
