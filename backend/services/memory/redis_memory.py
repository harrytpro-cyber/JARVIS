"""
Niveau 1 — Mémoire court terme Redis.
Clé : session:{user_id}  |  TTL : 7200s  |  Max : 30 messages (LTRIM)
"""
import json
import uuid
from datetime import datetime, timezone
from core.redis import get_redis

_PREFIX = "session"
_TTL = 7200
_MAX_MESSAGES = 30


def _key(user_id: uuid.UUID) -> str:
    return f"{_PREFIX}:{user_id}"


async def push_message(user_id: uuid.UUID, role: str, content: str, tokens: int = 0) -> None:
    r = await get_redis()
    k = _key(user_id)
    entry = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokens": tokens,
    })
    pipe = r.pipeline()
    pipe.rpush(k, entry)
    pipe.ltrim(k, -_MAX_MESSAGES, -1)   # garde les 30 derniers
    pipe.expire(k, _TTL)
    await pipe.execute()


async def get_messages(user_id: uuid.UUID) -> list[dict]:
    r = await get_redis()
    raw = await r.lrange(_key(user_id), 0, -1)
    return [json.loads(m) for m in raw]


async def clear_session(user_id: uuid.UUID) -> None:
    r = await get_redis()
    await r.delete(_key(user_id))


async def session_exists(user_id: uuid.UUID) -> bool:
    r = await get_redis()
    return bool(await r.exists(_key(user_id)))


async def refresh_ttl(user_id: uuid.UUID) -> None:
    r = await get_redis()
    await r.expire(_key(user_id), _TTL)
