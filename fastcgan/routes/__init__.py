from slowapi import Limiter
from slowapi.util import get_remote_address

from fastcgan.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10/minute"],
    storage_uri=settings.REDIS_RATE_LIMIT_URL,
)
