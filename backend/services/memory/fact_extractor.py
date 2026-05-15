"""
Fact Extractor — tourne en arrière-plan après chaque réponse.
Analyse la conversation avec Groq (rapide + économique) et extrait
les nouveaux faits à mémoriser, puis les sauvegarde dans pgvector.
"""
import asyncio
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from services.memory.vector_memory import save_memory
from core.config import settings

_EXTRACT_PROMPT = """Analyse cette conversation et extrait les faits importants sur l'utilisateur.
Réponds UNIQUEMENT avec un tableau JSON valide. Si aucun fait nouveau, retourne [].

Format : [{"content": "fait concis", "type": "preference|project|person|fact|decision|goal|task_context|emotion", "importance": 0.1-1.0}]

Règles :
- Ne retourne que des faits nouveaux non évidents
- Importance 0.9+ : décisions critiques, objectifs majeurs
- Importance 0.5-0.8 : préférences, contexte projet
- Importance < 0.5 : informations mineures
- Maximum 5 faits par échange
- Contenu en français, concis (max 120 chars)

Conversation :
{conversation}"""


async def extract_and_store(
    user_id: uuid.UUID,
    conversation: list[dict],
    session_factory: async_sessionmaker,
) -> None:
    """Lance l'extraction en tâche asyncio non bloquante."""
    asyncio.create_task(_run_extraction(user_id, conversation, session_factory))


async def _run_extraction(
    user_id: uuid.UUID,
    conversation: list[dict],
    session_factory: async_sessionmaker,
) -> None:
    if not settings.groq_api_key:
        return

    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}" for m in conversation[-6:]
    )

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)
        resp = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{
                "role": "user",
                "content": _EXTRACT_PROMPT.format(conversation=conv_text),
            }],
            temperature=0.1,
            max_tokens=512,
        )
        raw = resp.choices[0].message.content.strip()

        # Extrait le JSON même si le modèle ajoute du texte autour
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return
        facts: list[dict] = json.loads(raw[start:end])
    except Exception:
        return

    if not facts:
        return

    async with session_factory() as db:
        try:
            for fact in facts[:5]:
                content = fact.get("content", "").strip()
                if not content:
                    continue
                await save_memory(
                    db=db,
                    user_id=user_id,
                    content=content,
                    memory_type=fact.get("type", "fact"),
                    importance=float(fact.get("importance", 0.5)),
                )
            await db.commit()
        except Exception:
            await db.rollback()
