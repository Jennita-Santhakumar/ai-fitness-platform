"""
Rate limiting configuration using slowapi.
Provides a central Limiter instance based on client IP address.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance using client IP.
# headers_enabled is intentionally False: slowapi cannot inject rate-limit
# headers when endpoint handlers return plain Pydantic models (instead of
# starlette Response objects) — it raises an exception trying to mutate None.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
)
