"""
RAG Pipeline — orchestrateur de la mémoire 3 niveaux.

Séquence :
1. Redis      → 30 derniers messages de session
2. pgvector   → top-5 faits par cosine similarity
3. PostgreSQL → tâches + projets + briefing (≤ 800 tokens)
4. tiktoken   → compte les tokens totaux
5. Si > 6000  → résume les messages anciens avec Groq
6. Construit le prompt final → LLM Router
7. Background → Fact Extractor
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from models.user import User
from services.memory import redis_memory, vector_memory, working_memory
from services.memory.fact_extractor import extract_and_store
from services.llm_router import TaskType
from services.jarvis_personality import build_system_prompt
from core.config import settings

_TOKEN_BUDGET = 6000
_SUMMARY_KEEP = 6  # messages récents conservés intacts si résumé


def _count_tokens(text: str) -> int:
    """tiktoken si disponible, sinon estimation."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


async def _summarize_old_messages(messages: list[dict]) -> str:
    """Résume les messages anciens avec Groq pour réduire le contexte."""
    if not settings.groq_api_key:
        return "[historique tronqué]"
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)
        conv = "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in messages)
        resp = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{
                "role": "user",
                "content": f"Résume cette conversation en 3 phrases maximum, en conservant les faits clés :\n\n{conv}",
            }],
            max_tokens=256,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "[historique résumé indisponible]"


async def build_context_and_messages(
    db: AsyncSession,
    user: User,
    new_message: str,
    task_type: TaskType = TaskType.COMPLEX,
) -> tuple[str, list[dict]]:
    """
    Retourne (system_prompt_enrichi, messages_pour_llm).
    """
    user_id = user.id

    # ── Niveau 1 : Redis ─────────────────────────────────
    session_msgs = await redis_memory.get_messages(user_id)
    if not session_msgs:
        # Fallback : recharge depuis la dernière conversation PG
        from sqlalchemy import select
        from models.conversation import Conversation, Message
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        last_conv = result.scalar_one_or_none()
        if last_conv:
            msgs_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == last_conv.id)
                .order_by(Message.created_at.desc())
                .limit(30)
            )
            db_msgs = list(reversed(msgs_result.scalars().all()))
            session_msgs = [{"role": m.role, "content": m.content, "tokens": 0} for m in db_msgs]
            # Réhydrate Redis
            for m in session_msgs:
                await redis_memory.push_message(user_id, m["role"], m["content"])
        else:
            session_msgs = []

    # ── Niveau 2 : pgvector ───────────────────────────────
    similar_memories = await vector_memory.search_similar(db, user_id, new_message)
    memory_context = ""
    if similar_memories:
        lines = ["## Faits mémorisés pertinents"]
        for m in similar_memories:
            lines.append(f"- [{m.memory_type}] {m.content}")
        memory_context = "\n".join(lines)

    # ── Niveau 3 : PostgreSQL working memory ──────────────
    work_context = await working_memory.build_working_context(db, user_id)

    # ── Recherche web (si mots-clés détectés) ────────────
    from services.web_search_service import maybe_search_web
    web_context = await maybe_search_web(new_message)

    # ── Compte tokens + résumé si dépassement ────────────
    llm_messages = [{"role": m["role"], "content": m["content"]} for m in session_msgs]
    full_text = "\n".join(m["content"] for m in llm_messages) + new_message
    total_tokens = _count_tokens(full_text)

    if total_tokens > _TOKEN_BUDGET and len(llm_messages) > _SUMMARY_KEEP:
        old = llm_messages[:-_SUMMARY_KEEP]
        recent = llm_messages[-_SUMMARY_KEEP:]
        summary = await _summarize_old_messages(old)
        llm_messages = [
            {"role": "assistant", "content": f"[Résumé des échanges précédents] {summary}"},
            *recent,
        ]

    llm_messages.append({"role": "user", "content": new_message})

    # ── System prompt enrichi ─────────────────────────────
    base_system = build_system_prompt(
        username=user.full_name or user.username,
        mode=getattr(user, "jarvis_mode", "normal"),
    )
    extra_sections = [s for s in [memory_context, work_context, web_context] if s]
    if extra_sections:
        system = base_system + "\n\n" + "\n\n".join(extra_sections)
    else:
        system = base_system

    return system, llm_messages


async def post_response_tasks(
    user_id: uuid.UUID,
    conversation: list[dict],
    session_factory: async_sessionmaker,
) -> None:
    """Lance le Fact Extractor en arrière-plan."""
    await extract_and_store(user_id, conversation, session_factory)


def detect_memory_command(content: str) -> str | None:
    """
    Reconnaît les commandes mémoire utilisateur.
    Retourne le type de commande ou None.
    """
    cl = content.lower().strip()
    if cl.startswith("mémorise que") or cl.startswith("memorise que"):
        return "memorize"
    if cl.startswith("oublie "):
        return "forget"
    if "qu'est-ce que tu sais sur moi" in cl or "que sais-tu sur moi" in cl:
        return "list"
    if "efface toute ma mémoire" in cl or "supprime toute ma mémoire" in cl:
        return "delete_all"
    return None
