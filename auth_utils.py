from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from functools import wraps
from typing import Callable

def login_required(func: Callable):
    """Decorator to require authentication for a route"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)
        return await func(request, *args, **kwargs)
    return wrapper

def admin_required(func: Callable):
    """Decorator to require trip admin role for a route"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = request.session.get("user_id")
        trip_role = request.session.get("trip_role")
        
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)
        
        if trip_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin-Rechte erforderlich"
            )
        
        return await func(request, *args, **kwargs)
    return wrapper

def get_current_user(request: Request) -> dict:
    """Get current user info from session"""
    return {
        "id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "trip_role": request.session.get("trip_role"),
        "is_global_admin": request.session.get("is_global_admin", False),
        "is_authenticated": request.session.get("user_id") is not None,
        "is_trip_admin": request.session.get("trip_role") == "admin"
    }
