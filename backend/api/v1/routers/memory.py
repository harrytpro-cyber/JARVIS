import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from core.database import get_db
from api.v1.routers.auth import get_current_user
from services.memory.vector_memory import save_memory, list_top_memories, delete_memory, delete_all_memories
from services.memory import redis_memory
from models.memory import MEMORY_TYPES

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "fact"
    importance: float = 0.5
    project_id: uuid.UUID | None = None


class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    memory_type: str
    importance: float
    access_count: int
    created_at: str


@router.get("/", response_model=list[MemoryResponse])
async def get_memories(
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    memories = await list_top_memories(db, current_user.id, limit=limit)
    return [
        MemoryResponse(
            id=m.id,
            content=m.content,
            memory_type=m.memory_type,
            importance=m.importance,
            access_count=m.access_count,
            created_at=m.created_at.isoformat(),
        )
        for m in memories
    ]


@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.memory_type not in MEMORY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"memory_type invalide. Valeurs acceptées : {sorted(MEMORY_TYPES)}",
        )
    mem = await save_memory(
        db, current_user.id, body.content,
        memory_type=body.memory_type,
        importance=body.importance,
        project_id=body.project_id,
    )
    await db.commit()
    return MemoryResponse(
        id=mem.id,
        content=mem.content,
        memory_type=mem.memory_type,
        importance=mem.importance,
        access_count=mem.access_count,
        created_at=mem.created_at.isoformat(),
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_memory(
    memory_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_memory(db, current_user.id, memory_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir introuvable")


@router.delete("/", status_code=status.HTTP_200_OK)
async def wipe_all_memories(
    confirm: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if confirm != "CONFIRMER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passez confirm=CONFIRMER pour supprimer toute la mémoire.",
        )
    count = await delete_all_memories(db, current_user.id)
    await redis_memory.clear_session(current_user.id)
    await db.commit()
    return {"deleted": count, "message": f"{count} souvenir(s) supprimé(s)."}


@router.get("/session", summary="Contenu Redis de la session courante")
async def get_session(current_user=Depends(get_current_user)):
    messages = await redis_memory.get_messages(current_user.id)
    return {"count": len(messages), "messages": messages}


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session(current_user=Depends(get_current_user)):
    await redis_memory.clear_session(current_user.id)
