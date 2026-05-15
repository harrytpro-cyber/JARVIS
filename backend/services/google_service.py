"""
Google OAuth 2.0 — Gmail + Calendar.
Tokens chiffrés avec Fernet avant stockage.
"""
import urllib.parse
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from core.config import settings

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "openid",
    "email",
    "profile",
]


def get_auth_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_tok: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(_TOKEN_URL, data={
            "refresh_token": refresh_tok,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()


def token_expires_soon(expiry: datetime | None) -> bool:
    if not expiry:
        return True
    return expiry - datetime.now(timezone.utc) < timedelta(minutes=5)
