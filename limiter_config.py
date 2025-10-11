"""
Shared rate limiter configuration for the application.
This ensures all routes use the same limiter instance.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter instance used across the entire application
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/hour", "50/minute"]
)
