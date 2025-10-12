from fastapi.templating import Jinja2Templates
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor


def create_templates() -> Jinja2Templates:
    """Create Jinja2Templates instance with CSRF token processor"""
    templates = Jinja2Templates(
        directory="templates",
        context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
    )
    return templates
