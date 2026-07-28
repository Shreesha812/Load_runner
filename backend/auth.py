"""API key authentication dependency for FastAPI routes."""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _load_key() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.getenv("WOLKEN_API_KEY", "wolken-dev-key-change-me")


# Resolved once at import time — dotenv is loaded by main.py first
_API_KEY: str = _load_key()


async def require_api_key(x_api_key: str = Header(..., alias="X-Api-Key")) -> None:
    """FastAPI dependency — raises 401 if the key is missing or wrong."""
    if x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
