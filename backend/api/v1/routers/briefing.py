from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from api.v1.routers.auth import get_current_user
from services.briefing_service import get_or_generate

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/morning")
async def morning_briefing(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    city = getattr(current_user, "city", None) or "Paris"
    content = await get_or_generate(db, current_user.id, city)
    return {"content": content, "cached": True}
