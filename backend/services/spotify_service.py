"""
Contrôle Spotify via Web API.
Auth OAuth stockée chiffrée dans la table integrations.
"""
import httpx
from datetime import datetime, timezone
from core.config import settings
from core.crypto import encrypt, decrypt


_BASE = "https://api.spotify.com/v1"
_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SCOPES = "user-modify-playback-state user-read-playback-state streaming"


def get_auth_url(redirect_uri: str, state: str) -> str:
    import urllib.parse
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": _SCOPES,
        "state": state,
    }
    return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    import base64
    creds = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            headers={"Authorization": f"Basic {creds}"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_token(refresh_tok: str) -> dict:
    import base64
    creds = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            headers={"Authorization": f"Basic {creds}"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_tok},
        )
        resp.raise_for_status()
        return resp.json()


class SpotifyClient:
    def __init__(self, access_token: str):
        self._token = access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def play_pause(self, play: bool) -> None:
        async with httpx.AsyncClient() as c:
            endpoint = "play" if play else "pause"
            await c.put(f"{_BASE}/me/player/{endpoint}", headers=self._headers())

    async def next_track(self) -> None:
        async with httpx.AsyncClient() as c:
            await c.post(f"{_BASE}/me/player/next", headers=self._headers())

    async def prev_track(self) -> None:
        async with httpx.AsyncClient() as c:
            await c.post(f"{_BASE}/me/player/previous", headers=self._headers())

    async def set_volume(self, percent: int) -> None:
        async with httpx.AsyncClient() as c:
            await c.put(
                f"{_BASE}/me/player/volume",
                headers=self._headers(),
                params={"volume_percent": max(0, min(100, percent))},
            )

    async def search_and_play(self, query: str) -> dict | None:
        async with httpx.AsyncClient() as c:
            resp = await c.get(
                f"{_BASE}/search",
                headers=self._headers(),
                params={"q": query, "type": "track,artist", "limit": 1},
            )
            data = resp.json()
            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                return None
            track = tracks[0]
            await c.put(
                f"{_BASE}/me/player/play",
                headers=self._headers(),
                json={"uris": [track["uri"]]},
            )
            return {"name": track["name"], "artist": track["artists"][0]["name"]}

    async def current_track(self) -> dict | None:
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{_BASE}/me/player/currently-playing", headers=self._headers())
            if resp.status_code == 204:
                return None
            data = resp.json()
            item = data.get("item")
            if not item:
                return None
            return {
                "name": item["name"],
                "artist": item["artists"][0]["name"],
                "is_playing": data.get("is_playing", False),
            }
