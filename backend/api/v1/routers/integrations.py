"""
OAuth 2.0 — Google (Gmail + Calendar) + status.
Tokens chiffrés avec Fernet avant stockage.
"""
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.config import settings
from core.crypto import encrypt, decrypt
from api.v1.routers.auth import get_current_user
from models.integration import Integration
from services.google_service import (
    get_auth_url as google_auth_url,
    exchange_code as google_exchange,
    refresh_access_token as google_refresh,
    token_expires_soon,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])

_GOOGLE_REDIRECT = f"http://localhost:8000/api/v1/integrations/google/callback"


# ── Google ────────────────────────────────────────────────
@router.get("/google/auth")
async def google_auth(current_user=Depends(get_current_user)):
    state = f"{current_user.id}:{secrets.token_hex(16)}"
    url = google_auth_url(redirect_uri=_GOOGLE_REDIRECT, state=state)
    return {"auth_url": url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    user_id_str = state.split(":")[0]
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="State invalide")

    tokens = await google_exchange(code=code, redirect_uri=_GOOGLE_REDIRECT)
    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in", 3600)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    result = await db.execute(
        select(Integration).where(Integration.user_id == user_id, Integration.provider == "google")
    )
    integ = result.scalar_one_or_none()
    if integ:
        integ.access_token = encrypt(access)
        if refresh:
            integ.refresh_token = encrypt(refresh)
        integ.token_expiry = expiry
        integ.updated_at = datetime.now(timezone.utc)
    else:
        integ = Integration(
            id=uuid.uuid4(),
            user_id=user_id,
            provider="google",
            access_token=encrypt(access),
            refresh_token=encrypt(refresh) if refresh else None,
            token_expiry=expiry,
            scopes="gmail.readonly calendar",
        )
        db.add(integ)

    await db.commit()
    return {"status": "connected", "provider": "google"}


@router.get("/google/status")
async def google_status(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Integration).where(Integration.user_id == current_user.id, Integration.provider == "google")
    )
    integ = result.scalar_one_or_none()
    if not integ:
        return {"connected": False}
    return {
        "connected": True,
        "expires_soon": token_expires_soon(integ.token_expiry),
        "scopes": integ.scopes,
    }


async def get_valid_google_token(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Retourne un access token valide (rafraîchi si besoin)."""
    result = await db.execute(
        select(Integration).where(Integration.user_id == user_id, Integration.provider == "google")
    )
    integ = result.scalar_one_or_none()
    if not integ or not integ.access_token:
        return None
    if token_expires_soon(integ.token_expiry) and integ.refresh_token:
        ref = decrypt(integ.refresh_token)
        new_tokens = await google_refresh(ref)
        integ.access_token = encrypt(new_tokens["access_token"])
        integ.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=new_tokens.get("expires_in", 3600))
        await db.commit()
    return decrypt(integ.access_token)


# ── Gmail ─────────────────────────────────────────────────
@router.get("/gmail/emails")
async def list_emails(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import httpx
    token = await get_valid_google_token(db, current_user.id)
    if not token:
        raise HTTPException(status_code=401, detail="Google non connecté")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": "is:unread", "maxResults": 10},
        )
        return resp.json()


# ── Calendar ──────────────────────────────────────────────
@router.get("/calendar/events")
async def list_events(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import httpx
    from datetime import timezone
    token = await get_valid_google_token(db, current_user.id)
    if not token:
        raise HTTPException(status_code=401, detail="Google non connecté")
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "timeMin": now.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 20,
            },
        )
        return resp.json()
