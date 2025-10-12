from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect all routes except public ones.
    Redirects unauthenticated users to /login.
    """
    
    EXCLUDED_PATHS = [
        "/login",
        "/offline",
        "/static",
        "/favicon.ico",
        "/api"
    ]
    
    async def dispatch(self, request, call_next):
        # Check if path should be excluded from auth
        path = request.url.path
        
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return await call_next(request)
        
        # Check authentication
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)
        
        # User is authenticated, proceed
        response = await call_next(request)
        return response
