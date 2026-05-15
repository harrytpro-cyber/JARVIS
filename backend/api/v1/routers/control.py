"""
12 boutons du panneau de contrôle HUD.
pyautogui pour volume/screenshot, subprocess pour lancer les apps.
"""
import sys
import uuid
import subprocess
import base64
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.v1.routers.auth import get_current_user

router = APIRouter(prefix="/control", tags=["control"])

_WIN = sys.platform == "win32"


def _run(*args, shell: bool = False):
    try:
        subprocess.Popen(list(args), shell=shell, creationflags=subprocess.CREATE_NO_WINDOW if _WIN else 0)
        return True
    except Exception:
        return False


# ── Volume ──────────────────────────────────────────────
@router.post("/volume/up")
async def volume_up(_=Depends(get_current_user)):
    try:
        import pyautogui
        pyautogui.press("volumeup")
        return {"status": "ok", "action": "volume_up"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/volume/down")
async def volume_down(_=Depends(get_current_user)):
    try:
        import pyautogui
        pyautogui.press("volumedown")
        return {"status": "ok", "action": "volume_down"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Screenshot ───────────────────────────────────────────
@router.post("/screenshot")
async def take_screenshot(_=Depends(get_current_user)):
    try:
        import pyautogui
        img = pyautogui.screenshot()
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"status": "ok", "image_b64": b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Applications ─────────────────────────────────────────
_APP_COMMANDS = {
    "taskmgr": (["taskmgr"], True) if _WIN else (["gnome-system-monitor"], False),
    "chrome":  (["start", "chrome"], True) if _WIN else (["google-chrome"], False),
    "spotify": (["start", "spotify"], True) if _WIN else (["spotify"], False),
    "vscode":  (["code"], False),
}


@router.post("/launch/{app}")
async def launch_app(app: str, _=Depends(get_current_user)):
    if app not in _APP_COMMANDS:
        raise HTTPException(status_code=400, detail=f"App inconnue : {app}")
    cmd, shell = _APP_COMMANDS[app]
    ok = _run(*cmd, shell=shell)
    return {"status": "ok" if ok else "error", "app": app}


@router.post("/launch/mode-boulot")
async def mode_boulot(_=Depends(get_current_user)):
    results = {}
    for app in ["chrome", "spotify", "vscode"]:
        cmd, shell = _APP_COMMANDS[app]
        results[app] = "ok" if _run(*cmd, shell=shell) else "error"
    return {"status": "ok", "launched": results}


# ── Focus Timer ───────────────────────────────────────────
@router.post("/focus/start")
async def focus_start(minutes: int = 25, _=Depends(get_current_user)):
    return {"status": "ok", "duration_minutes": minutes, "action": "focus_started"}


# ── Recherche web rapide ──────────────────────────────────
class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def web_search(body: SearchRequest, _=Depends(get_current_user)):
    from services.web_search_service import search
    results = await search(body.query)
    return {"results": results}
