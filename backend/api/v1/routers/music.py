"""
Contrôle musique — Spotify (OAuth) + YouTube (ouvrir dans navigateur).
"""
import uuid
import secrets
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db
from core.config import settings
from core.crypto import encrypt, decrypt
from api.v1.routers.auth import get_current_user
from models.integration import Integration
from services.spotify_service import SpotifyClient, get_auth_url, exchange_code

router = APIRouter(prefix="/music", tags=["music"])

_SPOTIFY_REDIRECT = "http://localhost:8000/api/v1/music/spotify/callback"
_WIN = sys.platform == "win32"


async def _get_spotify_client(db: AsyncSession, user_id: uuid.UUID) -> SpotifyClient:
    result = await db.execute(
        select(Integration).where(Integration.user_id == user_id, Integration.provider == "spotify")
    )
    integ = result.scalar_one_or_none()
    if not integ or not integ.access_token:
        raise HTTPException(status_code=401, detail="Spotify non connecté")
    token = decrypt(integ.access_token)
    return SpotifyClient(token)


# ── OAuth Spotify ─────────────────────────────────────────
@router.get("/spotify/auth")
async def spotify_auth(current_user=Depends(get_current_user)):
    state = f"{current_user.id}:{secrets.token_hex(16)}"
    url = get_auth_url(redirect_uri=_SPOTIFY_REDIRECT, state=state)
    return {"auth_url": url}


@router.get("/spotify/callback")
async def spotify_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(state.split(":")[0])
    tokens = await exchange_code(code=code, redirect_uri=_SPOTIFY_REDIRECT)

    result = await db.execute(
        select(Integration).where(Integration.user_id == user_id, Integration.provider == "spotify")
    )
    integ = result.scalar_one_or_none()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))

    if integ:
        integ.access_token = encrypt(tokens["access_token"])
        if "refresh_token" in tokens:
            integ.refresh_token = encrypt(tokens["refresh_token"])
        integ.token_expiry = expiry
    else:
        integ = Integration(
            id=uuid.uuid4(), user_id=user_id, provider="spotify",
            access_token=encrypt(tokens["access_token"]),
            refresh_token=encrypt(tokens.get("refresh_token", "")),
            token_expiry=expiry,
        )
        db.add(integ)
    await db.commit()
    return {"status": "connected", "provider": "spotify"}


@router.get("/spotify/status")
async def spotify_status(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Integration).where(Integration.user_id == current_user.id, Integration.provider == "spotify")
    )
    integ = result.scalar_one_or_none()
    return {"connected": bool(integ and integ.access_token)}


# ── Contrôle playback ────────────────────────────────────
@router.post("/spotify/play")
async def play(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    await client.play_pause(True)
    return {"status": "playing"}


@router.post("/spotify/pause")
async def pause(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    await client.play_pause(False)
    return {"status": "paused"}


@router.post("/spotify/next")
async def next_track(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    await client.next_track()
    return {"status": "ok"}


@router.post("/spotify/prev")
async def prev_track(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    await client.prev_track()
    return {"status": "ok"}


class VolumeRequest(BaseModel):
    percent: int


@router.post("/spotify/volume")
async def set_volume(body: VolumeRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    await client.set_volume(body.percent)
    return {"status": "ok", "volume": body.percent}


class SearchRequest(BaseModel):
    query: str


@router.post("/spotify/search-play")
async def search_and_play(body: SearchRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    result = await client.search_and_play(body.query)
    if not result:
        raise HTTPException(status_code=404, detail="Aucun résultat Spotify")
    return {"status": "playing", "track": result}


@router.get("/spotify/current")
async def current_track(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_spotify_client(db, current_user.id)
    return await client.current_track() or {"status": "idle"}


# ── YouTube (ouvre dans navigateur) ──────────────────────
@router.post("/youtube/open")
async def youtube_open(body: SearchRequest, _=Depends(get_current_user)):
    query = urllib.parse.quote(body.query)
    url = f"https://www.youtube.com/results?search_query={query}"
    try:
        if _WIN:
            subprocess.Popen(["start", url], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen(["xdg-open", url])
        return {"status": "ok", "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
