"""
Application configuration loaded from environment variables and the local .env file.

This module uses python-decouple to read settings. By default, python-decouple will
look for values in the OS environment and then in a .env file at the project root.

Usage:
    from config import TAVILY_API

    # example: use the key with a client
    # client = TavilyClient(api_key=TAVILY_API)

Add more settings here as your project grows, for example:
    DEBUG: bool = _config('DEBUG', default=False, cast=bool)
    ALLOWED_HOSTS: list[str] = _config('ALLOWED_HOSTS', default='', cast=Csv())
"""
from __future__ import annotations

from decouple import config as _config, Csv

# Required settings
TAVILY_API: str = _config('tavily_api')  # from .env or environment; raises if missing

# Example optional settings (uncomment and use as needed)
# DEBUG: bool = _config('DEBUG', default=False, cast=bool)
# ALLOWED_HOSTS: list[str] = _config('ALLOWED_HOSTS', default='', cast=Csv())

__all__ = [
    'TAVILY_API',
    # 'DEBUG',
    # 'ALLOWED_HOSTS',
]
