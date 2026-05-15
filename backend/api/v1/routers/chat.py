import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db
from api.v1.routers.auth import get_current_user
from services.chat_service import ChatService
from models.conversation import Conversation, Message

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageRequest(BaseModel):
    content: str
    conversation_id: uuid.UUID | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: str

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    model_used: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/message")
async def send_message(
    body: MessageRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lance un stream SSE.
    Le client doit écouter GET /api/v1/chat/stream?conversation_id=...
    Ce endpoint crée/initialise la conversation et retourne son ID.
    """
    service = ChatService(db)
    conv = await service.get_or_create_conversation(current_user.id, body.conversation_id)
    await db.commit()
    return {"conversation_id": str(conv.id), "status": "ready"}


@router.get("/stream")
async def stream_chat(
    content: str,
    conversation_id: uuid.UUID | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events — répond token par token."""
    service = ChatService(db)
    return StreamingResponse(
        service.stream_chat(current_user, content, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            model_used=m.model_used,
            created_at=m.created_at.isoformat(),
        )
        for m in msgs
    ]
