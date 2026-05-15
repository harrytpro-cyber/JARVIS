"""
Niveau 2 — Mémoire épisodique pgvector.
Recherche cosine similarity, déduplication à 0.92, RLS via current_setting.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete, func
from models.memory import Memory, MEMORY_TYPES
from services.memory.embedder import embed

_SIMILARITY_DEDUP = 0.92
_TOP_K = 5


async def _set_rls_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Active le RLS pour la requête courante."""
    await db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))


async def search_similar(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    top_k: int = _TOP_K,
    memory_type: str | None = None,
) -> list[Memory]:
    await _set_rls_user(db, user_id)
    vec = await embed(query)
    vec_str = "[" + ",".join(str(v) for v in vec) + "]"

    q = (
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(text(f"embedding <=> '{vec_str}'::vector"))
        .limit(top_k)
    )
    if memory_type:
        q = q.where(Memory.memory_type == memory_type)

    result = await db.execute(q)
    memories = list(result.scalars().all())

    # Met à jour access_count + last_accessed
    for m in memories:
        m.access_count += 1
        m.last_accessed = datetime.now(timezone.utc)
    await db.flush()
    return memories


async def save_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: str,
    memory_type: str = "fact",
    importance: float = 0.5,
    project_id: uuid.UUID | None = None,
) -> Memory:
    if memory_type not in MEMORY_TYPES:
        memory_type = "fact"

    vec = await embed(content)

    # Déduplication : similarité > 0.92 → mise à jour plutôt que création
    existing = await _find_duplicate(db, user_id, vec)
    if existing:
        existing.content = content
        existing.importance = max(existing.importance, importance)
        existing.access_count += 1
        existing.last_accessed = datetime.now(timezone.utc)
        await db.flush()
        return existing

    memory = Memory(
        id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        content=content,
        embedding=vec,
        memory_type=memory_type,
        importance=importance,
    )
    db.add(memory)
    await db.flush()
    return memory


async def _find_duplicate(
    db: AsyncSession, user_id: uuid.UUID, vec: list[float]
) -> Memory | None:
    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
    result = await db.execute(
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(text(f"embedding <=> '{vec_str}'::vector"))
        .limit(1)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None or candidate.embedding is None:
        return None
    # Calcule la similarité cosine manuellement
    similarity = await db.scalar(
        text(f"SELECT 1 - (embedding <=> '{vec_str}'::vector) FROM memories WHERE id = '{candidate.id}'")
    )
    return candidate if (similarity or 0) >= _SIMILARITY_DEDUP else None


async def delete_memory(db: AsyncSession, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    return result.rowcount > 0


async def list_top_memories(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[Memory]:
    result = await db.execute(
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.access_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_all_memories(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        delete(Memory).where(Memory.user_id == user_id)
    )
    return result.rowcount
