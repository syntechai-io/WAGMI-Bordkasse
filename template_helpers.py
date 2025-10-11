from fastapi.templating import Jinja2Templates
from starlette.requests import Request


def get_csrf_token(request: Request) -> str:
    """Extract CSRF token from request cookies"""
    return request.cookies.get("csrftoken", "")


def create_templates() -> Jinja2Templates:
    """Create Jinja2Templates with CSRF token support"""
    templates = Jinja2Templates(directory="templates")
    templates.env.globals["csrf_token"] = get_csrf_token
    return templates
